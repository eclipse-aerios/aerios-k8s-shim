'''
Module to support communication with K8s API
'''
# import base64
from kubernetes import client
from kubernetes.client.rest import ApiException
from app.utils import get_app_logger
from app.app_config import WIREGUARD_CONFIGMAP_NAME, DNSMASQ_CONFIGMAP_NAME

logger = get_app_logger()


def get_k8s_secret(secret_name: str, namespace: str):
    '''
    Get secret from K8s API
    Args:
        secret_name (str): the name of the secret to retrieve from K8s API
        namespace (str): the K8s namespace
    Returns:
        secret (str): the K8s secret object
    '''
    try:
        v1 = client.CoreV1Api()
        secret = v1.read_namespaced_secret(secret_name, namespace)
        return secret
    except ApiException as e:
        if e.status == 404:
            return None
        else:
            raise e


def get_key_from_secret(secret, key):
    '''
    Get key value from secret
    '''
    try:
        # The 'data' field contains the base64-encoded values
        if key in secret.data:
            # Base64 decode the secret value
            # decoded_value = base64.b64decode(secret.data[key]).decode('utf-8')
            # return decoded_value
            return secret.data[key]
        else:
            logger.info("Key %s not found in the secret.", key)
            return None

    except client.exceptions.ApiException as e:
        logger.error("Exception when reading secret: %s", e)
        return None


def create_k8s_secret(secret_name: str, namespace: str, secret_data: any):
    '''
    Create secret using K8s API
    Args:
        secret_name (str): the name of the secret to retrieve from K8s API
        namespace (str): the K8s namespace
        secret_data: the oject to store in K8s secret
    '''
    v1 = client.CoreV1Api()
    secret = client.V1Secret(metadata=client.V1ObjectMeta(name=secret_name),
                             data=secret_data)
    v1.create_namespaced_secret(namespace=namespace, body=secret)


def update_k8s_secret(secret_name: str, namespace: str, secret_data: any):
    '''
    Update secret using K8s API
    Args:
        secret_name (str): the name of the secret to retrieve from K8s API
        namespace (str): the K8s namespace
        secret_data: the oject to store in K8s secret
    '''
    v1 = client.CoreV1Api()
    secret = client.V1Secret(metadata=client.V1ObjectMeta(name=secret_name),
                             data=secret_data)
    v1.replace_namespaced_secret(name=secret_name,
                                 namespace=namespace,
                                 body=secret)


def create_k8s_configmap_object(namespace: str, configmap_name: str,
                                config_data: str) -> bool:
    '''
    Create K8s configmap
    Args:
        namespace (str): the requested namespace for the configmap
        configmap_name (str): the name of the configmap to be used inside K8s
        config_data (str): the configmap as a string
    Returns:   
        True/False upon success or not
    '''
    v1 = client.CoreV1Api()
    logger.info("NAME: %s", configmap_name)
    if configmap_name == WIREGUARD_CONFIGMAP_NAME:
        conf_file_name = "wg0.conf"
    elif configmap_name == DNSMASQ_CONFIGMAP_NAME:
        conf_file_name = "dnsmasq.conf"
    else:
        logger.error(
            "Configmap name not recognised, should be one of wg-configmap or dnsmaq-configmap"
        )
        return False
    config_map = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(name=configmap_name),
        data={conf_file_name: config_data})
    try:
        v1.replace_namespaced_config_map(name=configmap_name,
                                         namespace=namespace,
                                         body=config_map)
    except ApiException as e:
        if e.status == 404:
            v1.create_namespaced_config_map(namespace=namespace,
                                            body=config_map)
        else:
            return False
    return True


def get_k8s_configmap_object(namespace: str, configmap_name: str):
    """
    Retrieve a ConfigMap from a Kubernetes cluster.

    Args:
        namespace (str): The namespace where the ConfigMap is located.
        config_map_name (str): The name of the ConfigMap to retrieve.

    Returns:
        dict: The ConfigMap data if found, or None if not found.
    """
    try:
        # Create an instance of the API class
        v1 = client.CoreV1Api()
        logger.info("NAME: %s", configmap_name)

        # Get the ConfigMap
        config_map = v1.read_namespaced_config_map(name=configmap_name,
                                                   namespace=namespace)
        if configmap_name == WIREGUARD_CONFIGMAP_NAME:
            config_key = "wg0.conf"
        elif configmap_name == DNSMASQ_CONFIGMAP_NAME:
            config_key = "dnsmasq.conf"
        else:
            logger.error(
                "Configmap name not recognised, should be one of wg-configmap or dnsmaq-configmap"
            )
            return False

        config = config_map.data.get(config_key, None)

        # Return the ConfigMap data
        return config

    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(
                f"ConfigMap '{configmap_name}' not found in namespace '{namespace}'."
            )
            return None
        else:
            print(f"An error occurred: {e}")
            return None


def restart_pod(namespace: str, pod_label: str) -> bool:
    '''
    Restart a K8s pod.
    Args:
        namespace (str): which namespace the pods live on
        pod_label (str): the label to retrieve pod
    Returns:
        True/False upon success or not
    '''
    v1 = client.CoreV1Api()
    # Find the WireGuard pod and delete it to trigger a restart
    pod_list = v1.list_namespaced_pod(namespace=namespace,
                                      label_selector=pod_label)
    if not pod_list.items:
        return False

    for pod in pod_list.items:
        v1.delete_namespaced_pod(name=pod.metadata.name, namespace=namespace)

    return True
