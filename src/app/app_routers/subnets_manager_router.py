"""
Routers for handling local subnets for overlays
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.utils import get_app_logger
from app import subnets_handler

router = APIRouter()
logger = get_app_logger()


class SubnetRequest(BaseModel):
    '''
    Model body for requests
    '''
    service_id: str


@router.post("/subnet")
def assign_subnet(request: SubnetRequest):
    """
    Assign an unused /24 subnet to the given service ID.

    POST /subnet
    """
    service_id = request.service_id
    success, r = subnets_handler.assign_subnet(service_id=service_id)

    if not success:
        raise HTTPException(status_code=400, detail=r)

    return {"service_id": service_id, "assigned_subnet": r}


@router.delete("/subnet")
def release_subnet(request: SubnetRequest):
    """
    Release the subnet assigned to the given service ID.

    DELETE /subnet
    """
    service_id = request.service_id
    success, released_subnet = subnets_handler.release_subnet(
        service_id=service_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=
            f"Service ID '{service_id}' does not have an assigned subnet.")

    return {"service_id": service_id, "released_subnet": released_subnet}


@router.get("/subnet/{service_id}")
def get_assigned_subnet(service_id: str):
    """
    Retrieve the subnet assigned to the given service ID.
    
    GET /subnet/{service_id}
    """
    success, assigned_subnet = subnets_handler.get_assigned_subnet(
        service_id=service_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=
            f"Service ID '{service_id}' does not have an assigned subnet.")

    return {"service_id": service_id, "assigned_subnet": assigned_subnet}


@router.get("/subnets")
def list_subnets():
    """
    List all assigned and available subnets.
    
    GET /subnets
    """
    logger.info("Listing all available and assigned subnets.")
    available_subnets_list, allocated_subnets_dict = subnets_handler.list_subnets(
    )
    return {
        "available_subnets": available_subnets_list,
        "assigned_subnets": allocated_subnets_dict,
    }


@router.delete("/subnets")
def reset_subnets():
    """
    Reset all subnets to their initial state.
    
    DELETE /subnets
    """
    available_subnets_list, allocated_subnets_dict = subnets_handler.reset_subnets(
    )
    return {
        "message": "Subnet management system reset to initial state.",
        "available_subnets": available_subnets_list,
        "assigned_subnets": allocated_subnets_dict,
    }
