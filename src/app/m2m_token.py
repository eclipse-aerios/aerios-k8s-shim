'''
Class which handles token for m2m comunication
Undertakes interaction with k8s to store and retrieve from a secret object and
           access to Keycloak API to retrieve tokens
'''
# Constants for Kubernetes Secrets and Keycloak
from datetime import datetime, timedelta
import base64
import requests
from app import app_config
from app.utils import get_app_logger
from app.api_clients import k8s_shim


class M2mToken:
    '''
    Class which handles tokens needed for m2m communication.
    Used (intially by HLO) to access CB and HLO Local AL EP.
    Retrives tokens from Keycloak based on pre-configured client_id and client secret.
    Stores and updates K8s secret objects with values.
    Checks tokens validity (expried ot not) and updates.
    '''

    def __init__(self, m2m_type: str):
        """
        Initialize the environment with an m2m mode.

        Args:
            m2m_type (str): The type of m2m shold be 'cb' or 'hlo'.
        
        Raises:
            ValueError: If mode is not 'cb' or 'hlo'.
        """
        # config.load_incluster_config() ## for within cluster

        self.logger = get_app_logger()

        if m2m_type not in ["cb", "hlo"]:
            raise ValueError("mode must be either 'cb' or 'hlo'")
        self.namespace = app_config.NAMESPACE_M2M_CLIENTS

        if m2m_type == "cb":
            self.secret_name = app_config.SECRET_NAME_CB
            self.client_id = app_config.CLIENT_ID_CB
            self.client_secret = app_config.CLIENT_SECRET_CB
        elif m2m_type == "hlo":
            self.secret_name = app_config.SECRET_NAME_HLO
            self.client_id = app_config.CLIENT_ID_HLO
            self.client_secret = app_config.CLIENT_SECRET_HLO
        # self.set_kube_context(context_name="madrid-ncsrd-demo")

    def get_k8s_secret(self):
        '''
        Get secret holding keycloack m2m token from K8s API
        Args:
            m2m_type (str): cb|hlo
        Returns:
        token (str): the keycloak token
        '''
        secret = k8s_shim.get_k8s_secret(secret_name=self.secret_name,
                                         namespace=self.namespace)
        return secret

    def create_k8s_secret(self, token, expires_at):
        '''
        Create secret to hold keycloack m2m token in K8s
        Args:
            token (str): token from Keycloak
            expires_at (str): expiration date from keycloak
        '''
        data = {
            "token": base64.b64encode(token.encode()).decode(),
            "expires_at": base64.b64encode(expires_at.encode()).decode()
        }
        k8s_shim.create_k8s_secret(secret_name=self.secret_name,
                                   namespace=self.namespace,
                                   secret_data=data)

    def update_k8s_secret(self, token, expires_at):
        '''
        Update secret holding keycloack m2m token in K8s (e.g. once expired)
        Args:
            token (str): token from Keycloak
            expires_at (str): expiration date from keycloak
        '''
        data = {
            "token": base64.b64encode(token.encode()).decode(),
            "expires_at": base64.b64encode(expires_at.encode()).decode()
        }
        k8s_shim.update_k8s_secret(secret_name=self.secret_name,
                                   namespace=self.namespace,
                                   secret_data=data)

    def get_keycloak_token(self):
        """
        Use client_id and client_secret as provided from Keycloack instance to retrieve m2m token
        Returns:
            token (str): keycloak token
            expires_at (str): expiration date
            or None if failed to succesfully get token from Keycloack
        """
        if app_config.DEV:
            self.logger.info(
                "We do not have secret in K8s secret object for secret: %s. Ready to access Keycloack API!",
                self.secret_name)
            self.logger.info('Using => CLIENT ID: %s, CLIENT SECRET: %s',
                             self.client_id, self.client_secret)
        payload = f'client_id={self.client_id}&client_secret={self.client_secret}&grant_type=client_credentials'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        url = f"{app_config.KEYCLOAK_URL}/auth/realms/{app_config.REALM_OPENLDAP}/protocol/openid-connect/token"
        response = requests.request("POST",
                                    url,
                                    headers=headers,
                                    data=payload,
                                    timeout=5,
                                    verify=False)

        if response.status_code != 200:
            return None

        token_data = response.json()
        token = token_data['access_token']
        expires_in = token_data['expires_in']
        expires_at = (datetime.utcnow() +
                      timedelta(seconds=expires_in)).isoformat()
        if app_config.DEV:
            self.logger.info("TOKEN RECEIVED: %s", token)

        return token, expires_at

def get_m2m_token(m2m_token_type: str):
    '''
    Undertake all the process to return m2m tokens
    Arg: 
      m2m_token_type: this should either be cb or hlo
    Retrun:
      Base64 encoded token
    '''
    _m2m = M2mToken(m2m_type=m2m_token_type)
    secret = _m2m.get_k8s_secret()

    if secret is None:
        # Secret not found, get token from Keycloak and create the secret
        token, expires_at = _m2m.get_keycloak_token()
        _m2m.create_k8s_secret(token, expires_at)
        return {"token": token}

    # Secret found, decode it
    token = base64.b64decode(secret.data['token']).decode()
    expires_at = base64.b64decode(secret.data['expires_at']).decode()
    expires_at_dt = datetime.fromisoformat(expires_at)

    if datetime.utcnow() >= expires_at_dt:
        # Token expired, get a new one and update the secret
        token, expires_at = _m2m.get_keycloak_token()
        _m2m.update_k8s_secret(token, expires_at)
    return token