'''
    Some common utility objects and functions
'''
import os
import logging
from kubernetes import config as k8s_config
from requests.exceptions import RequestException, HTTPError, Timeout
from app import app_config


def catch_requests_exceptions(func):
    '''
        Docstring
    '''
    logger = get_app_logger()

    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except HTTPError as e:
            logger.info("4xx or 5xx: %s \n", {e})
            return None  # raise our custom exception or log, etc.
        except ConnectionError as e:
            logger.info(
                "Raised for connection-related issues\
                      (e.g., DNS resolution failure, network issues): %s \n",
                {e})
            return None  # raise our custom exception or log, etc.
        except Timeout as e:
            logger.info("Timeout occured: %s \n", {e})
            return None  # raise our custom exception or log, etc.
        except RequestException as e:
            logger.info("Request failed: %s \n", {e})
            return None  # raise our custom exception or log, etc.

    return wrapper


async def set_kube_context():
    """
    Set the Kubernetes context for the client.
    """
    logger = get_app_logger()
    if app_config.DEV:
        # Load the kubeconfig file
        logger.info("In development mode trying to use context: %s",
                    app_config.DEV_CTX_NAME)
        k8s_config.load_kube_config(config_file=app_config.DEV_CTX_PATH,
                                    context=app_config.DEV_CTX_NAME)
        logger.info("Connected to %s context.", app_config.DEV_CTX_NAME)

    else:
        # Load the in-cluster configuration, which uses the ServiceAccount
        #    as defined in K8s deployment (deployment.yaml file)
        logger.info("Connecting to K8s API.")
        k8s_config.load_incluster_config()  ## for within cluster
        logger.info("OK, Connected to K8s API.")


def check_log_path_exists():
    '''
        Docstring
    '''
    if not os.path.exists(app_config.PARENT_PATH + "/log"):
        os.makedirs(app_config.PARENT_PATH + "/log")


def get_app_logger():
    '''
        Docstring
    '''

    check_log_path_exists()

    app_logger = logging.getLogger('hlo-fe-logger')

    if not app_logger.handlers:
        logger = logging.getLogger('hlo-fe-logger')
        logger.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            '%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d:%H:%M:%S')

        file_handler = logging.FileHandler(app_config.LOG_PATH)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        return logger

    return app_logger


def remove_block_from_string(str_item: str, start_str: str, stop_str: str):
    '''
    Removes all lines between (and including):
     start_str and stop_str
    Used to remove service registries in wg and dnsmaq configmaps 
    '''
    lines = str_item.splitlines()
    result = []
    inside_block = False  # Tracks whether we're inside the block to remove

    for line in lines:
        if start_str in line:
            inside_block = True  # Enter the block
            continue  # Skip the line
        if stop_str in line:
            inside_block = False  # Exit the block
            continue  # Skip the line
        if not inside_block:
            result.append(line)  # Add lines that are not in the block

    # Join the remaining lines back into a string
    return "\n".join(result)
