import contextlib
from tenant_schemas.utils import schema_context

from api.provider.models import Provider, ProviderAuthentication, ProviderBillingSource
from api.models import Customer, Tenant
from django.test import TestCase, TransactionTestCase
from django.db import connection, transaction
from django.core.management import call_command

from masu.tests.database.helpers import ReportObjectCreator
from api.iam.test.iam_test_case import IamTestCase

class MasuTestCase(TestCase):
    """Subclass of TestCase that automatically create an app and client."""

    @classmethod
    def setUpClass(cls):
        """Create test case setup."""
        super().setUpClass()
        with schema_context('public'):
            cls.schema = 'acct10001'
            cls.acct = '10001'
            cls.customer = Customer.objects.create(account_id=cls.acct,
                                                   schema_name=cls.schema)
            cls.tenant = Tenant(schema_name=cls.schema)
            cls.tenant.save()

        cls.aws_db_auth_id = '1'
        cls.ocp_db_auth_id = '2'
        cls.ocp_test_provider_uuid = '3c6e687e-1a09-4a05-970c-2ccf44b0952e'
        cls.aws_test_provider_uuid = '6e212746-484a-40cd-bba0-09a19d132d64'
        cls.aws_provider_resource_name = 'arn:aws:iam::111111111111:role/CostManagement'
        cls.ocp_provider_resource_name = 'my-ocp-cluster-1'
        cls.aws_test_billing_source = 'test-bucket'
        cls.ocp_test_billing_source = None

        aws_auth = ProviderAuthentication.objects.create(
            id=cls.aws_db_auth_id,
            uuid='7e4ec31b-7ced-4a17-9f7e-f77e9efa8fd6',
            provider_resource_name=cls.aws_provider_resource_name
        )
        aws_auth.save()
        aws_billing_source = ProviderBillingSource.objects.create(
            bucket=cls.aws_test_billing_source
        )
        aws_billing_source.save()

        cls.aws_provider = Provider.objects.create(
            uuid=cls.aws_test_provider_uuid,
            name='Test Provider',
            type='AWS',
            authentication=aws_auth,
            billing_source=aws_billing_source,
            customer=cls.customer,
            setup_complete=False)
        cls.aws_provider.save()
