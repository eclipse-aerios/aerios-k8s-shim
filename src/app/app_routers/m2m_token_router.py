'''
Endpoints for m2m token
'''
from fastapi import APIRouter, HTTPException, Path
from app.m2m_token import get_m2m_token
from app.utils import get_app_logger
from app.domain_pk_generator import update_k8s_wg_secret

router = APIRouter()

logger = get_app_logger()


@router.get(
    "/token/{m2m_token_type}",
    summary="Retrieve M2M Token",
    description=
    "API endpoint for aeriOSS components to get machine-to-machine (M2M) token based on the token type (`cb` for CB or `hlo` for HLO Local AL EP).",
    response_description="The M2M token based on the provided type (cb|hlo).",
    tags=["M2m AuthN/Z"],
    responses={
        200: {
            "description": "Successful retrieval of M2M token",
            "content": {
                "application/json": {}
            }
        },
        400: {
            "description": "Invalid token type (must be 'cb' or 'hlo')."
        },
        500: {
            "description": "Internal Server Error"
        }
    })
def get_token(m2m_token_type: str = Path(..., regex="^(cb|hlo)$")):
    """
    API endpoint for aeriOSS components to get M2M token.

    Args:
        m2m_token_type (str): cb | hlo (either to access CB or HLO Local AL EP).

    Returns:
        Json with "token" key containing the token value.
    """
    logger.info("Received token request call with for m2m type: %s",
                m2m_token_type)

    token = get_m2m_token(m2m_token_type=m2m_token_type)

    if not token:
        raise HTTPException(status_code=500,
                            detail="Failed to get token from Keycloak")

    logger.info("Token sent to client: %s", token)
    return {"token": token}


@router.patch(
    "/create-wg-domain-secret",
    summary="Update WireGuard Domain Secret",
    description="""
    API endpoint to update a Kubernetes secret containing WireGuard domain-specific information.
    This secret is  to store sensitive information related to WireGuard configuration.
    Private and Public key are created on component startup.
    This endpoint is exposed in case, for any reason, we want to update this pair
    """,
    response_description="WireGuard domain secret udpated successfully.",
    tags=["Domain"],
    responses={
        200: {
            "description": "WireGuard domain secret update successfully."
        },
        400: {
            "description": "Invalid input or configuration error."
        },
        500: {
            "description": "Internal server error during secret creation."
        }
    })
async def update_wireguard_domain_secret():
    '''
    API Endpoint to update wireguard keys.
    Private key is pushed in K8s secret
    Public key is pushed on aeriOSS continuum Domain entity
    Returns:
        A success message or an error depending on the update result.
    '''
    await update_k8s_wg_secret()
    return {"message": "WireGuard domain secret udpated successfully."}
