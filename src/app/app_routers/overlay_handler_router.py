'''
Expose endpooints to create and release registrations for overlays:
  Includes update wg and dnsmaq configuration (configmaps)
  Restart wg/dnsmaq pods
  Delete allocated subnet (for release overlay)
Endpoints abstract interaction with K8s substrate ...and more
'''
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from app.wg_server_configurator import ServiceOverlayRequest, setup_k8s_domain_wg
from app import subnets_handler
from app.utils import get_app_logger

router = APIRouter()

logger = get_app_logger()


@router.post("/service-network-overlay",
             summary="Configure WireGuard Server",
             description="""
    API endpoint for aeriOS HLO to configure the WireGuard server when setting up an overlay.
    This is used for service components' direct communication.
    One peer should to be marked as master (wg server)
    
    Example payload for `peers`:
    ```json
    [
        {
            "name": "wg-server",
            "peer_public_key": "eXf93YG023jt+Srjls43lR81VQ/rXBz+eWv+ewUBHlI=",
            "peer_overlay_ip": "10.13.13.1",
            "is_master": true
        },
        {
            "name": "vasilis-wg",
            "public_key": "eXf93YG023jt+Srjls43lR81VQ/rXBz+eWv+ewUBHlI=",
            "allowed_ips": "10.13.13.2/32"
        },
        {
            "name": "john-wg",
            "public_key": "eXf93YG023jt+Srjls43lR81VQ/rXBz+eWv+ewUBHlI=",
            "allowed_ips": "10.13.13.3/32"
        }
    ]
    ```
    """,
             response_description=
             "Configuration of WireGuard server successfully updated.",
             responses={
                 200: {
                     "description":
                     "WireGuard configuration updated successfully"
                 },
                 400: {
                     "description": "Invalid input data"
                 },
                 500: {
                     "description": "Internal server error"
                 }
             })
async def create_service_overlay(request: ServiceOverlayRequest):
    """
    API endpoint for aeriOS HLO to configure WireGuard server when setting up an overlay.
    
    Args:
        peers (List[Peer]): A list of Peer objects containing fields for
                             WireGuard and Dnsmaq configuration for each peer.
            Peer object:
             name: str
             peer_public_key: str
             peer_overlay_ip: str
             is_master: bool = None
        One peer is expected to be the wg server, i.e. has the property "is_master" and set to true 

    """
    service_id = request.service_id
    peers = request.peers
    logger.info("Peers list received: %s", peers)
    success, message = setup_k8s_domain_wg(service_id=service_id, peers=peers)
    if not success:
        raise HTTPException(status_code=500, detail=message)

    logger.info("WireGuard configuration updated and pod restarted. %s",
                message)

    return {"detail": "WireGuard configuration updated and pod restarted"}


class DeleteServiceOverlayRequest(BaseModel):
    '''
    Represents delete-wireguard-overlay expected body
    '''
    service_id: str


@router.delete(
    "/service-network-overlay",
    summary="Delete overlay of service",
    description=("""
        This endpoint deletes the overlay of service based on the provided service ID. 
        The client must send the `service_id` as part of the JSON payload.
        Addressing services for which local domain is the handler domain
        """),
    response_description=
    "A message indicating whether the service was successfully deleted.")
async def delete_service_overlay(request: DeleteServiceOverlayRequest):
    """
    Deletes a service using the provided service ID.

    Args:
        request (DeleteServiceOverlayRequest): A JSON object containing the service_id.

    Returns:
        dict: A JSON response with a success message or error details.

    Raises:
        HTTPException: If the service ID is not found or an error occurs during deletion.
    """
    service_id = request.service_id
    # Remove from k8s wg and dnsmasq
    success, message = setup_k8s_domain_wg(service_id=service_id, peers=None)
    if not success:
        raise HTTPException(status_code=500, detail=message)
    # Delete also subnet from allocated_aubnets
    success, released_subnet = subnets_handler.release_subnet(
        service_id=service_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"failed to release subnet for service {service_id}")

    logger.info("WireGuard configuration updated and pod restarted. %s",
                message)

    return {
        "detail":
        f"WireGuard configuration updated, pod restarted, subnet {released_subnet} released"
    }
