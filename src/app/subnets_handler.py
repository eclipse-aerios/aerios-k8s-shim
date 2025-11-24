'''
Module to handle overlay subnets LCM
'''
from app.app_config import available_subnets_list, allocated_subnets_dict, SUBNET_BASE
from app.utils import get_app_logger

logger = get_app_logger()


def release_subnet(service_id: str) -> tuple[bool, str]:
    '''
    Find subnet allocated to service with id:
        remove it from allocated subnets dictinairy (by id)
        added it to available subnets list
    Input:
        service_id: the service whith allocated subnet
    Output:
        (bool, str): Success (not), released subnet 

    '''
    if service_id not in allocated_subnets_dict:
        logger.error("Service ID %s does not have an assigned subnet.",
                     service_id)
        return False, ""

    # Release the subnet
    released_subnet = allocated_subnets_dict.pop(service_id)
    available_subnets_list.append(released_subnet)
    available_subnets_list.sort()  # Keep subnets in order
    logger.info("Released subnet  %s for service ID %s.", release_subnet,
                service_id)
    return True, released_subnet


def assign_subnet(service_id: str) -> tuple[bool, str]:
    '''
    Allocate subnet to service id:
        remove it from available subnets list 
        added allocated subnets dictionairy (by id)
    Input:
        service_id: str, the service whith allocated subnet
    Output:
        (bool, str): Success or not, released subnet or failure message 
    '''
    if service_id in allocated_subnets_dict:
        logger.error("Service ID %s already has an assigned subnet.",
                     service_id)
        return (True, allocated_subnets_dict[service_id])
        # return False, "Service ID %s already has an assigned subnet."

    if not available_subnets_list:
        logger.error("No available subnets to assign.")
        return False, "No available subnets to assign"

    # Assign the first available subnet
    assigned_subnet = available_subnets_list.pop(0)
    allocated_subnets_dict[service_id] = assigned_subnet
    logger.info("Assigned subnet %s to service ID %s.", assign_subnet,
                service_id)
    return True, assigned_subnet


def get_assigned_subnet(service_id: str) -> tuple[bool, str]:
    '''
    Retrieve subnet allocated to service id
    Get it from allocated subnets dictionairy by id
    Input:
        service_id: str, the service whith allocated subnet
    Output:
        (bool, str): Success or not, released subnet or failure message    
    '''
    if service_id not in allocated_subnets_dict:
        logger.error("Service ID %s does not have an assigned subnet.",
                     service_id)
        return False, ""

    assigned_subnet = allocated_subnets_dict[service_id]
    logger.info("Retrieved assigned subnet %s for service ID %s.",
                assign_subnet, service_id)
    return True, assigned_subnet


def list_subnets():
    '''
    Return all assigned and available subnets.
    Output:
        Tuple: (list of str, dict of [id,str])
    '''
    return available_subnets_list, allocated_subnets_dict


def reset_subnets():
    '''
    Reset all subnets to their initial state.
    '''
    available_subnets_list[:] = [f"{SUBNET_BASE}.{i}.0/24" for i in range(256)]
    allocated_subnets_dict.clear()
    logger.info(
        "Subnet management system has been reset to its initial state.")
    return available_subnets_list, allocated_subnets_dict
