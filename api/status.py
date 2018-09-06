#
# Copyright 2018 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

"""View for server status."""

import logging
import os
import platform
import subprocess
import sys

import psycopg2
from flask import jsonify, request

from masu.api import API_VERSION
from masu.celery import celery as celery_app
from masu.config import Config
from masu.external.date_accessor import DateAccessor
from masu.util.blueprint import application_route

LOG = logging.getLogger(__name__)

API_V1_ROUTES = {}

BROKER_CONNECTION_ERROR = 'Unable to establish connection with broker.'
CELERY_WORKER_NOT_FOUND = 'No running Celery workers were found.'


@application_route('/status/', API_V1_ROUTES, methods=('GET',))
def get_status():
    """Packages response for class-based view."""
    if 'liveness' in request.args:
        return jsonify({'alive': True})

    app_status = ApplicationStatus()
    response = {
        'api_version': app_status.api_version,
        'celery_status': app_status.celery_status,
        'commit': app_status.commit,
        'current_datetime': app_status.current_datetime,
        'database_status': app_status.database_status,
        'debug': app_status.debug,
        'modules': app_status.modules,
        'platform_info': app_status.platform_info,
        'python_version': app_status.python_version
    }
    return jsonify(response)


# pylint: disable=too-few-public-methods, no-self-use
class ApplicationStatus():
    """A view that returns status JSON."""

    api_version = API_VERSION

    def __init__(self):
        """Initialize an ApplicationStatus object."""
        self._events = dict()
        self.modules = {}

    @property
    def celery_status(self):
        """Determine the status of our connection to Celery.

        :returns: dict of celery status, or an error
        """
        # First check if our Broker is reachable
        conn = None
        try:
            conn = celery_app.connection()
            conn.heartbeat_check()
        except ConnectionRefusedError:
            return {'Error': BROKER_CONNECTION_ERROR}
        # Now check if Celery workers are running
        stats = self._check_celery_status()
        if 'Error' in stats and stats['Error'] != CELERY_WORKER_NOT_FOUND:
            stats = self._check_celery_status()
        if conn:
            conn.release()
        return stats

    def _check_celery_status(self):
        """Check for celery status."""
        try:
            conn = celery_app.connection()
            inspector = celery_app.control.inspect(
                connection=conn,
                timeout=1
            )
            stats = inspector.stats()
            if not stats:
                stats = {'Error': CELERY_WORKER_NOT_FOUND}
        except ConnectionResetError as err:
            stats = {'Error': str(err)}
        finally:
            if conn:
                conn.release()
        return stats

    @property
    def commit(self):
        """
        Collect the build number for the server.

        :returns: A build number

        """
        commit_info = os.environ.get('OPENSHIFT_BUILD_COMMIT', None)
        if not commit_info:
            commit_info = subprocess.run(['git',
                                          'describe',
                                          '--always'],
                                         stdout=subprocess.PIPE)
            if commit_info.stdout:
                commit_info = commit_info.stdout.decode('utf-8').strip()
        return commit_info

    @property
    def database_status(self):
        """Collect database connection information.

        :returns: A dict of db connection info.
        """
        try:
            with psycopg2.connect(Config.SQLALCHEMY_DATABASE_URI) as conn:
                curs = conn.cursor()
                curs.execute(
                    """
                    SELECT datname AS database,
                        numbackends as database_connections
                    FROM pg_stat_database
                    """
                )
                raw = curs.fetchall()

                # get pg_stat_database column names
                names = [desc[0] for desc in curs.description]
        except (psycopg2.InterfaceError,
                psycopg2.NotSupportedError,
                psycopg2.OperationalError,
                psycopg2.ProgrammingError) as exc:
            LOG.warning('Unable to connect to DB: %s', str(exc))
            return {'ERROR': str(exc)}

        # transform list-of-lists into list-of-dicts including column names.
        result = [dict(zip(names, row)) for row in raw]

        return result

    @property
    def platform_info(self):
        """Collect the platform information.

        :returns: A dictionary of platform data
        """
        return platform.uname()._asdict()

    @property
    def python_version(self):
        """Collect the python version information.

        :returns: The python version string.
        """
        return sys.version.replace('\n', '')

    @property
    def modules(self):
        """Collect the installed modules.

        :returns: A dictonary of module names and versions.
        """
        return self._modules

    # pylint: disable=unused-argument
    @modules.setter
    def modules(self, value):
        module_data = {}
        for name, module in sorted(sys.modules.items()):
            if hasattr(module, '__version__'):
                module_data[str(name)] = str(module.__version__)
        # pylint: disable=attribute-defined-outside-init
        self._modules = module_data

    @property
    def current_datetime(self):
        """Collect the service current datetime.

        :returns: The datetime string.
        """
        return DateAccessor().today()

    @property
    def debug(self):
        """Collect the debug state of the service.

        :returns: Boolean indicating debug status.
        """
        return Config.DEBUG

    def startup(self):
        """Log startup information."""
        LOG.info(f'API Version: {self.api_version}')
        LOG.info(f'Celery Status: {self.celery_status}')
        LOG.info(f'Commit: {self.commit}')
        LOG.info(f'Current Date: {self.current_datetime}')
        LOG.info(f'DEBUG enabled: {str(self.debug)}')
        LOG.info(f'Database: {self.database_status}')

        LOG.info('Platform:')
        for name, value in self.platform_info.items():
            LOG.info(f'{name} - {value}')

        LOG.info('Python: %s', self.python_version)
        module_list = []
        for mod, version in list(self.modules.items()):
            module_list.append(f'{mod} - {version}')

        if module_list:
            LOG.info('Modules: %s', ', '.join(module_list))
        else:
            LOG.info('Modules: None')
