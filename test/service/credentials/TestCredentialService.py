from unittest import TestCase
from os.path import abspath, join, dirname

from src.exception.CredentialCurrentlyAvailableError import CredentialCurrentlyAvailableError
from src.exception.NoAvailableCredentialsError import NoAvailableCredentialsError
from src.service.credentials.CredentialService import CredentialService


class TestCredentialService(TestCase):

    def setUp(self) -> None:
        CredentialService.CREDENTIALS_PATH = f"{abspath(join(dirname(__file__), '../..'))}/resources/test_credentials.json"
        self.target = CredentialService()

    def tearDown(self) -> None:
        # This has to be done because we are testing a Singleton
        CredentialService._instances.clear()

    def test_get_credentials_available_when_none_occupied(self):
        credential = self.target.get_credentials('test-service')
        assert credential is not None
        assert credential.id == 'rdr'

    def test_get_credentials_available_when_one_occupied(self):
        _ = self.target.get_credentials('test-service')
        credential = self.target.get_credentials('test-service')
        assert credential is not None
        assert credential.id == 'fg'

    def test_get_credentials_raise_exception_when_all_occupied(self):
        _ = self.target.get_credentials('test-service')
        _ = self.target.get_credentials('test-service')
        with self.assertRaises(NoAvailableCredentialsError) as context:
            _ = self.target.get_credentials('test-service')
        assert context.exception is not None
        assert context.exception.message == 'All credentials are being used by service: test-service.'

    def test_get_credentials_available_for_service_when_occupied_for_other_service(self):
        credential_service1 = self.target.get_credentials('test-service-1')
        credential_service2 = self.target.get_credentials('test-service-2')
        assert credential_service1 is not None
        assert credential_service2 is not None
        assert credential_service1.id == credential_service2.id

    def test_get_credentials_available_for_service_when_other_service_saturated(self):
        _ = self.target.get_credentials('test-service-1')
        _ = self.target.get_credentials('test-service-1')
        credential = self.target.get_credentials('test-service-2')
        assert credential is not None

    def test_unlock_credentials_ok(self):
        credential = self.target.get_credentials('test-service')
        self.target.unlock_credentials(credential.id, 'test-service')

    def test_unlock_non_used_credential_raises_exception(self):
        with self.assertRaises(CredentialCurrentlyAvailableError) as context:
            self.target.unlock_credentials('some-id', 'test-service')
        assert context.exception is not None
        assert context.exception.message == 'Credential with key some-id-test-service is currently available.'

    def test_get_unlock_get_again_ok(self):
        credential = self.target.get_credentials('test-service')
        first_id = credential.id
        self.target.unlock_credentials(credential.id, 'test-service')
        credential = self.target.get_credentials('test-service')
        assert credential.id == first_id