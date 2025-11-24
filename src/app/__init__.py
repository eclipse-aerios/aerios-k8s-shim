'''
Docstring
'''
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.app_routers import subnets_manager_router, overlay_handler_router, m2m_token_router
from app import utils
from app import domain_pk_generator

# FastAPI object customization
FASTAPI_TITLE = "aeriOS-k8s-shim"
FASTAPI_DESCRIPTION = "A bridge for aeriOS to k8s native interaction"
FASTAPI_VERSION = "0.109.0"
FASTAPI_OPEN_API_URL = "/"
FASTAPI_DOCS_URL = "/docs"

logger = utils.get_app_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    '''
    Lifespan to handle application life cycle events. 
    '''
    # Startup: Code here will run when the app starts
    logger.info(
        "Starting up... Initializing resources. Setting kube context and creating wg private/public keys"
    )

    # Call custom bootstrap functions
    await utils.set_kube_context()
    await domain_pk_generator.create_k8s_wg_secret()

    # Yield control to the application
    yield

    # Shutdown: Code here will run when the app shuts down
    logger.info("Shutting down... Cleaning up resources")


# Create FastAPI app and use lifespan
_app = FastAPI(title=FASTAPI_TITLE,
               description=FASTAPI_DESCRIPTION,
               version=FASTAPI_VERSION,
               docs_url=FASTAPI_DOCS_URL,
               openapi_url=FASTAPI_OPEN_API_URL,
               lifespan=lifespan)

_app.include_router(router=overlay_handler_router,
                    tags=["Overlays Management"])
_app.include_router(router=subnets_manager_router, tags=["Subnets Management"])
_app.include_router(router=m2m_token_router)
