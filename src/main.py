'''
    Run this with:
      uvicorn main:_app --host 0.0.0.0 --port 8000 --reload
'''
from app import _app, app_config, utils

utils.check_log_path_exists()
logger = utils.get_app_logger()
logger.info('**aeriOS-K8s-shim started**')
logger.info("App is in development mode: %s", app_config.DEV)
logger.info("KEYCLOAK_URL: %s", app_config.KEYCLOAK_URL)
logger.info("REALM_OPENLDAP: %s", app_config.REALM_OPENLDAP)
if app_config.DEV:
    logger.info("CLIENT_ID_CB: %s", app_config.CLIENT_ID_CB)
    logger.info("CLIENT_CB_SECRET: %s", app_config.CLIENT_SECRET_CB)
    logger.info("CLIENT_ID_HLO: %s", app_config.CLIENT_ID_HLO)
    logger.info("CLIENT_SECRET_HLO: %s", app_config.CLIENT_SECRET_HLO)
    logger.info("PRIVATE KEY NAME: %s", app_config.PRIVATE_KEY_SECRET_NAME)
    logger.info("PUBLIC KEY NAME: %s", app_config.PUBLIC_KEY_SECRET_NAME)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(_app, host="0.0.0.0", port=8000)
