'''
Module to handle aerOS domain private and public key generation
'''
import subprocess
from app.utils import get_app_logger
from app.api_clients import k8s_shim
from app.api_clients.cb_client import CBClient
from app.app_config import SECRET_NAME, PRIVATE_KEY_SECRET_NAME, PUBLIC_KEY_SECRET_NAME, \
                           NAMESPACE_WG, DEV

logger = get_app_logger()


def _register_public_key(public_key: str):
    '''
    Register domain public key to the continuum. 
    Update local domain entity with publicKey attribute.
    First we query local domain id (loca=true ngsild flag).
    Then we update (patch) domain entity with public key. Again local=true.
    :input
    @param public_key: the public key to push to the continuum
    '''
    cb_client = CBClient()
    domain_name_ngsild_params = "type=Domain&format=simplified&local=true"
    # Thue use of 'local=true' ensures that we only have one,
    # and there is always one record in the response list (local_domain_obj)
    local_domain_list = cb_client.query_entities(
        ngsild_params=domain_name_ngsild_params)
    # So we can safely retrieve the first, and only, element and get the id
    #    which is the id of the local domain.
    local_domain_id = local_domain_list[0]['id']
    update_obj = {"publicKey": {"type": "Property", "value": public_key}}
    if DEV:
        logger.info(update_obj)
        logger.info(public_key)
    ngsild_params = 'local=true'
    cb_client.patch_entity(entity_id=local_domain_id,
                           upd_object=update_obj,
                           ngsild_params=ngsild_params)
    logger.info(
        "aeriOS continuum local Domain entity: %s updated with public key: %s",
        local_domain_id, public_key)


def _generate_wireguard_keys():
    '''
    Generate wireguard keys.
    Requires wg cli installed in container
    Keys are base64 encoded (as required by wireguard)
    '''
    # Generate private key
    private_key = subprocess.check_output(['wg', 'genkey']).strip()

    # Generate public key using the private key
    process = subprocess.Popen(['wg', 'pubkey'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    public_key, _ = process.communicate(input=private_key)
    public_key = public_key.strip()

    return private_key.decode('utf-8'), public_key.decode('utf-8')


async def create_k8s_wg_secret():
    '''
    Create namespaced K8s secret object with aeriOS domain private key
    Private key is pushed to K8s secret
    Public key is pushed to aeriOS continuum aeriOS domain entity
    '''
    logger.info("Creating private and public key for aeriOS domain")
    try:
        key_exists = k8s_shim.get_k8s_secret(secret_name=SECRET_NAME,
                                             namespace=NAMESPACE_WG)
        if not key_exists:
            logger.info("Key not found creating new")
            private_key, public_key = _generate_wireguard_keys()
            if DEV:
                logger.info("Private key: %s", private_key)
                logger.info("Public key: %s", public_key)
                logger.info("Private key K8s secret name: %s",
                            PRIVATE_KEY_SECRET_NAME)
                logger.info("Public key K8s secret name: %s",
                            PUBLIC_KEY_SECRET_NAME)
            # Both keys are already base64 encoded,as provided from wg tool
            data = {
                PRIVATE_KEY_SECRET_NAME: private_key,
                PUBLIC_KEY_SECRET_NAME: public_key
            }
            if DEV:
                logger.info("DATA: %s", data)
            k8s_shim.create_k8s_secret(secret_name=SECRET_NAME,
                                       namespace=NAMESPACE_WG,
                                       secret_data=data)
            _register_public_key(public_key=public_key)

        else:
            logger.info("Keys  already exists, doing nothing.")
            # MOVE TO UPDATE
            # k8s_shim.update_k8s_secret(secret_name=SECRET_NAME,
            #                            namespace=NAMESPACE,
            #                            secret_data=data)
    except Exception as ex:
        logger.error(ex)


async def update_k8s_wg_secret():
    '''
    Update namespaced K8s secret object with aeriOS domain private key
    Private key updates K8s secret
    Public key udpates aeriOS continuum aeriOS domain entity
    '''
    logger.info("Updating private and public key for aeriOS domain")
    try:
        private_key, public_key = _generate_wireguard_keys()
        if DEV:
            logger.info("Private key: %s", private_key)
            logger.info("Public key: %s", public_key)
            logger.info("Private key: %s", PRIVATE_KEY_SECRET_NAME)
            logger.info("Public key: %s", PUBLIC_KEY_SECRET_NAME)
        data = {
            PRIVATE_KEY_SECRET_NAME: private_key,
            PUBLIC_KEY_SECRET_NAME: public_key
        }
        if DEV:
            logger.info("DATA: %s", data)
        k8s_shim.update_k8s_secret(secret_name=SECRET_NAME,
                                   namespace=NAMESPACE_WG,
                                   secret_data=data)
        _register_public_key(public_key=public_key)
    except Exception as ex:
        logger.error(ex)
