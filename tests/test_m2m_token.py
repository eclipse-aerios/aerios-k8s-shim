import base64
import importlib.util
import logging
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_PATH))

app = types.ModuleType("app")
app.__path__ = [str(SRC_PATH / "app")]

app_config = types.ModuleType("app.app_config")
app_config.DEV = False
app_config.NAMESPACE_M2M_CLIENTS = "default"
app_config.SECRET_NAME_CB = "keycloak-token-secret-cb"
app_config.SECRET_NAME_HLO = "keycloak-token-secret-hlo"
app_config.KEYCLOAK_URL = "https://keycloak.front-research-group.eu"
app_config.REALM_OPENLDAP = "realm"
app_config.CLIENT_ID_CB = "cb-client"
app_config.CLIENT_SECRET_CB = "cb-secret"
app_config.CLIENT_ID_HLO = "hlo-client"
app_config.CLIENT_SECRET_HLO = "hlo-secret"

utils = types.ModuleType("app.utils")
utils.get_app_logger = lambda: logging.getLogger("test")

api_clients = types.ModuleType("app.api_clients")
k8s_shim = types.ModuleType("app.api_clients.k8s_shim")
api_clients.k8s_shim = k8s_shim

app.app_config = app_config
app.utils = utils
app.api_clients = api_clients

sys.modules["app"] = app
sys.modules["app.app_config"] = app_config
sys.modules["app.utils"] = utils
sys.modules["app.api_clients"] = api_clients
sys.modules["app.api_clients.k8s_shim"] = k8s_shim

spec = importlib.util.spec_from_file_location(
    "app.m2m_token", SRC_PATH / "app" / "m2m_token.py")
m2m_token = importlib.util.module_from_spec(spec)
sys.modules["app.m2m_token"] = m2m_token
spec.loader.exec_module(m2m_token)
get_m2m_token = m2m_token.get_m2m_token


class Secret:
    def __init__(self, token, expires_at):
        self.data = {
            "token": base64.b64encode(token.encode()).decode(),
            "expires_at": base64.b64encode(expires_at.encode()).decode(),
        }


class FakeM2mToken:
    secret = None
    keycloak_tokens = []
    created_secrets = []
    updated_secrets = []

    def __init__(self, m2m_type):
        self.m2m_type = m2m_type

    def get_k8s_secret(self):
        return self.secret

    def get_keycloak_token(self):
        return self.keycloak_tokens.pop(0)

    def create_k8s_secret(self, token, expires_at):
        self.created_secrets.append((token, expires_at))

    def update_k8s_secret(self, token, expires_at):
        self.updated_secrets.append((token, expires_at))


class GetM2mTokenTest(unittest.TestCase):
    def setUp(self):
        FakeM2mToken.secret = None
        FakeM2mToken.keycloak_tokens = []
        FakeM2mToken.created_secrets = []
        FakeM2mToken.updated_secrets = []

    @patch("app.m2m_token.M2mToken", FakeM2mToken)
    def test_first_retrieval_creates_secret_and_returns_token_string(self):
        FakeM2mToken.keycloak_tokens = [("new-token", "2030-01-01T00:00:00")]

        result = get_m2m_token("cb")

        self.assertEqual(result, "new-token")
        self.assertEqual(FakeM2mToken.created_secrets,
                         [("new-token", "2030-01-01T00:00:00")])
        self.assertEqual(FakeM2mToken.updated_secrets, [])

    @patch("app.m2m_token.M2mToken", FakeM2mToken)
    def test_unexpired_secret_returns_stored_token_without_refresh(self):
        expires_at = (datetime.now(timezone.utc) +
                      timedelta(minutes=6)).isoformat()
        FakeM2mToken.secret = Secret("stored-token", expires_at)

        result = get_m2m_token("cb")

        self.assertEqual(result, "stored-token")
        self.assertEqual(FakeM2mToken.created_secrets, [])
        self.assertEqual(FakeM2mToken.updated_secrets, [])

    @patch("app.m2m_token.M2mToken", FakeM2mToken)
    def test_secret_within_refresh_window_refreshes_token(self):
        expires_at = (datetime.now(timezone.utc) +
                      timedelta(minutes=4, seconds=59)).isoformat()
        FakeM2mToken.secret = Secret("nearly-expired-token", expires_at)
        FakeM2mToken.keycloak_tokens = [("refreshed-token",
                                         "2030-01-01T00:00:00")]

        result = get_m2m_token("cb")

        self.assertEqual(result, "refreshed-token")
        self.assertEqual(FakeM2mToken.created_secrets, [])
        self.assertEqual(FakeM2mToken.updated_secrets,
                         [("refreshed-token", "2030-01-01T00:00:00")])

    @patch("app.m2m_token.M2mToken", FakeM2mToken)
    def test_expired_secret_refreshes_token_and_updates_secret(self):
        expires_at = (datetime.now(timezone.utc) -
                      timedelta(seconds=1)).isoformat()
        FakeM2mToken.secret = Secret("expired-token", expires_at)
        FakeM2mToken.keycloak_tokens = [("refreshed-token",
                                         "2030-01-01T00:00:00")]

        result = get_m2m_token("cb")

        self.assertEqual(result, "refreshed-token")
        self.assertEqual(FakeM2mToken.created_secrets, [])
        self.assertEqual(FakeM2mToken.updated_secrets,
                         [("refreshed-token", "2030-01-01T00:00:00")])


if __name__ == "__main__":
    unittest.main()
