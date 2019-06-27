import contextlib
from tenant_schemas.utils import schema_context

from api.provider.models import Provider, ProviderAuthentication, ProviderBillingSource
from api.models import Customer
from django.test import TestCase, TransactionTestCase
from django.db import connection
from django.core.management import call_command

from masu.tests.database.helpers import ReportObjectCreator
from api.iam.test.iam_test_case import IamTestCase

class MasuTestCase(IamTestCase):
    """Subclass of TestCase that automatically create an app and client."""

    def setUp(self):
        """Create test case setup."""

        self.account = '10001'
        super().setUp()
        #with schema_context(self.schema):
        #self.customer = Customer.objects.create(account_id=self.account,
        #                                        schema_name=self.schema)
        self.schema = self.schema_name

        self.aws_db_auth_id = '1'
        self.ocp_db_auth_id = '2'
        self.ocp_test_provider_uuid = '3c6e687e-1a09-4a05-970c-2ccf44b0952e'
        self.aws_test_provider_uuid = '6e212746-484a-40cd-bba0-09a19d132d64'
        self.aws_provider_resource_name = 'arn:aws:iam::111111111111:role/CostManagement'
        self.ocp_provider_resource_name = 'my-ocp-cluster-1'
        self.aws_test_billing_source = 'test-bucket'
        self.ocp_test_billing_source = None

        aws_auth = ProviderAuthentication.objects.create(
            id=self.aws_db_auth_id,
            uuid='7e4ec31b-7ced-4a17-9f7e-f77e9efa8fd6',
            provider_resource_name=self.aws_provider_resource_name
        )
        aws_auth.save()
        aws_billing_source = ProviderBillingSource.objects.create(
            bucket=self.aws_test_billing_source
        )
        aws_billing_source.save()

        self.aws_provider = Provider.objects.create(
            uuid=self.aws_test_provider_uuid,
            name='Test Provider',
            type='AWS',
            authentication=aws_auth,
            billing_source=aws_billing_source,
            customer=self.customer,
            setup_complete=False)
        self.aws_provider.save()
