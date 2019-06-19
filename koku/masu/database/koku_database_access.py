#
# Copyright 2018 Red Hat, Inc.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""Accessor for Customer information from koku database."""

import logging

from django.db import transaction, IntegrityError
from tenant_schemas.utils import schema_context

LOG = logging.getLogger(__name__)


class KokuDBAccess:
    """Base Class to connect to the koku database."""

    # pylint: disable=no-member
    def __init__(self, schema):
        """
        Establish database connection.

        Args:
            schema       (String) database schema (i.e. public or customer tenant value)
        """
        self.schema = schema
        # self._db = DB_ENGINE
        # self._meta = self._create_metadata()
        # self._session_factory = sessionmaker(bind=self._db)
        # self._session_registry = scoped_session(self._session_factory)
        # self._session = self._create_session()
        # self._base = self._prepare_base()
        self._savepoint = None

    def __enter__(self):
        """Context manager entry."""
        self._savepoint = transaction.savepoint()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        """Context manager close session."""
        with schema_context(self.schema):
            if exception_type:
                transaction.savepoint_rollback(self._savepoint)
            else:
                transaction.savepoint_commit(self._savepoint)

    def _get_db_obj_query(self, **filter_args):
        """
        Return the sqlachemy query for this table .

        Args:
            None
        Returns:
            (sqlalchemy.orm.query.Query): "SELECT public.api_customer.group_ptr_id ..."
        """
        with schema_context(self.schema):
            queryset = self._table.objects.all()
            if filter_args:
                queryset = queryset.filter(**filter_args)
            return queryset

    def does_db_entry_exist(self):
        """
        Return status for the existence of an object in the database.

        Args:
            None
        Returns:
            (Boolean): "True/False",
        """
        with schema_context(self.schema):
            return self._get_db_obj_query().exists()

    def add(self, **kwargs):
        """
        Add a new row to this table.

        Args:
            kwargs (Dictionary): Fields containing table attributes.

        Returns:
            (Object): new model object

        """
        with schema_context(self.schema):
            new_entry = self._table.objects.create(**kwargs)
            return new_entry

    def delete(self, obj=None):
        """
        Delete our object from the database.

        Args:
            obj (object) model object to delete
        Returns:
            None
        """
        if obj:
            deleteme = obj
        else:
            deleteme = self._obj
        with schema_context(self.schema):
            deleteme.delete()

    def savepoint(self, func, *args, **kwargs):
        """Wrap a db access function in a savepoint block.

        For more info, see:
            https://docs.sqlalchemy.org/en/latest/orm/session_transaction.html#using-savepoint

        Args:
            func (bound method) a function reference.
            args (object) function's positional arguments
            kwargs (object) function's keyword arguments
        Returns:
            None

        """
        with schema_context(self.schema):
            try:
                savepoint = transaction.savepoint()
                func(*args, **kwargs)
                transaction.savepoint_commit(savepoint)

            except IntegrityError as exc:
                LOG.warning('query transaction failed: %s', exc)
                transaction.savepoint_rollback(savepoint)
