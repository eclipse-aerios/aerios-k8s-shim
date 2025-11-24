'''
Module configuration
'''
import os
from decouple import config as env_config

# DEV related configuration
# when code pushed to gitlab pipeline convert DEV to False(no need to change)
DEV = False
DEV_CTX_PATH = "/home/vpitsilis/.kube/config"
DEV_CTX_NAME = "mvp-ncsrd-domain"

# Logging related values
PARENT_PATH = os.path.dirname(__file__)
LOG_PATH = PARENT_PATH + '/log/aeriOS-k8s-shim.log'

# K8s related configuration
if DEV:
    NAMESPACE_WG = "default"
    NAMESPACE_M2M_CLIENTS = "default"
    SECRET_NAME_CB = "keycloak-token-secret-cb"
    SECRET_NAME_HLO = "keycloak-token-secret-hlo"
    KEYCLOAK_URL = "https://keycloak.cf-mvp-domain.aeros-project.eu"
    REALM_OPENLDAP = "keycloack-openldap"
    CLIENT_ID_CB = "ContextBroker"
    CLIENT_SECRET_CB = "cYTiPucIBIuBAXbl2Igf9tIgTkQSiWUv"
    CLIENT_ID_HLO = "HLO"
    CLIENT_SECRET_HLO = "kXo0LqfQGYdjEHoWUtRKiMDBgjptTqDP"
    SECRET_NAME = "wg-secret-keys"
    PRIVATE_KEY_SECRET_NAME = "private-key"
    PUBLIC_KEY_SECRET_NAME = "public-key"
    WIREGUARD_CONFIGMAP_NAME = "wg-configmap"
    DNSMASQ_CONFIGMAP_NAME = "dnsmasq-configmap"
    WIREGUARD_POD_LABEL = "app=wireguard"
    # Orion-LD configuration
    CB_URL = 'http://10.220.2.101'  # <=== node IP for node port
    CB_PORT = '31026'  # <== exposed node port
    URL_VERSION = 'ngsi-ld/v1/'
    OVERLAY_SUBNET = '10.13.0.0'

else:
    NAMESPACE_WG = env_config('NAMESPACE_WG')
    NAMESPACE_M2M_CLIENTS = env_config('NAMESPACE_M2M_CLIENTS')
    SECRET_NAME_CB = env_config('SECRET_NAME_CB')
    SECRET_NAME_HLO = env_config('SECRET_NAME_HLO')
    KEYCLOAK_URL = env_config('KEYCLOAK_URL')
    REALM_OPENLDAP = env_config('REALM_OPENLDAP')
    CLIENT_ID_CB = env_config('CLIENT_ID_CB')
    CLIENT_SECRET_CB = env_config('CLIENT_SECRET_CB')
    CLIENT_ID_HLO = env_config('CLIENT_ID_HLO')
    CLIENT_SECRET_HLO = env_config('CLIENT_SECRET_HLO')
    SECRET_NAME = env_config('SECRET_NAME')
    PRIVATE_KEY_SECRET_NAME = env_config('PRIVATE_KEY_SECRET_NAME')
    PUBLIC_KEY_SECRET_NAME = env_config('PUBLIC_KEY_SECRET_NAME')
    WIREGUARD_CONFIGMAP_NAME = env_config('WIREGUARD_CONFIGMAP_NAME')
    DNSMASQ_CONFIGMAP_NAME = env_config('DNSMASQ_CONFIGMAP_NAME')
    WIREGUARD_POD_LABEL = env_config('WIREGUARD_POD_LABEL')
    CB_URL = env_config(
        'CB_URL')  # "http://orion-ld-broker.default.svc.cluster.local"
    CB_PORT = env_config('CB_PORT')  # 1026
    URL_VERSION = 'ngsi-ld/v1/'
    OVERLAY_SUBNET = env_config('OVERLAY_SUBNET')

# Global variables for subnet management
subnet_parts = OVERLAY_SUBNET.split(".")
SUBNET_BASE = f"{subnet_parts[0]}.{subnet_parts[1]}"
available_subnets_list = [f"{SUBNET_BASE}.{i}.0/24"
                          for i in range(256)]  # Available /24 subnets
allocated_subnets_dict: dict[str, str] = {
}  # Mapping of service_id to assigned subnets
