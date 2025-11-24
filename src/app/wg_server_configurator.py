'''
Module for upadting aeriOS wire-guard server configuration 
and deploy network overlay for connected clients
'''
import ipaddress
from pydantic import BaseModel
from app.api_clients import k8s_shim
from app import app_config
from app import utils


class Peer(BaseModel):
    '''
    Model peer configuration
    '''
    name: str
    peer_public_key: str
    peer_overlay_ip: str
    is_master: bool = None


class ServiceOverlayRequest(BaseModel):
    '''
    Request to request service overlay
    '''
    service_id: str
    peers: list[Peer]


class WgServerConfig:
    '''
        Manage network overlay for services: create delete, reset.
        On create we have both service_id and peers to add
        On delete we have service id but peers object is empty
        On reset no service id is provided, we just set intial configuration for wg and dnsmaq
        When creating service overlay:  
            public_key, peer_overlay_ip are used for wireguard server configuration
            name, peer_overlay_ip is used for dnsmaq server configuration
            One entry is expected to be the wg server (is_master exists and is true)
    '''

    def __init__(self, service_id: str, peers: list[Peer]):
        self.service_id = service_id
        self.peers = peers
        # Check details of wg server, the one with "is_master" true field
        if service_id:  # we are asked to update configmaps of wg and dnsmaq for a service
            if peers:  # we are on create overlay for service
                self.wg_server = next(
                    (peer for peer in peers if peer.is_master), None)
                self.wg_server_ip = ipaddress.ip_address(
                    address=self.wg_server.peer_overlay_ip)
                self.wg_client_peers = [
                    peer for peer in peers if not peer.is_master
                ]
            else:  # we are on a delete service overlay
                pass
        else:  # we are in reset configmaps call
            self.wg_server_ip = ipaddress.ip_address(
                address=app_config.OVERLAY_SUBNET) + 1
        self.namespace = app_config.NAMESPACE_WG
        self.pod_label = app_config.WIREGUARD_POD_LABEL
        self.configmap_wg_name = app_config.WIREGUARD_CONFIGMAP_NAME
        self.configmap_dnsmasq_name = app_config.DNSMASQ_CONFIGMAP_NAME
        self.logger = utils.get_app_logger()
        self.logger.info("Initializing wg configurator")
        full_key_object = k8s_shim.get_k8s_secret(
            secret_name=app_config.SECRET_NAME,
            namespace=app_config.NAMESPACE_WG)
        self.private_key = k8s_shim.get_key_from_secret(
            secret=full_key_object, key=app_config.PRIVATE_KEY_SECRET_NAME)
        self.logger.info("Got from K8s private key: %s", self.private_key)
        # private_key = "iELN6zGpzemkkJyo2jBSDlBuIE/J8PW67Poi66xpFHs="
        self.config_wg_data = ""
        self.config_dnsmaq_data = ""

    def is_valid(self):
        '''
        Check object is valid
        Do as needed
        Extend as needed.
        '''
        return self.wg_server is not None

    def generate_wireguard_config(self):
        '''
        Create wireguard server conf file.
        Server part is fix.
        For peers we create something  like this:
        peers = [
            {
                "name": "vasilis-wg",
                "public_key": "eXf93YG023jt+Srjls43lR81VQ/rXBz+eWv+ewUBHlI=",
                "allowed_ips": "10.13.13.2/32",
            },
            {
                "name": "john-wg",
                "public_key": "somePublicKeyHere",
                "allowed_ips": "10.13.13.3/32",
            }
        ]
        '''
        # CASE A: Dynamic, extend existing configuration,
        #         for the case of extending the wg constantly
        wg_config = k8s_shim.get_k8s_configmap_object(
            namespace=self.namespace, configmap_name=self.configmap_wg_name)
        # Modify the 'Address' line by appending the new server ip in the new subnet
        updated_lines = []
        for line in wg_config.splitlines():
            if line.startswith("Address"):
                if f"{str(self.wg_server_ip)}/24" not in line:
                    # Append the new server ipd
                    line = f"{line}, {str(self.wg_server_ip)}/24"
            updated_lines.append(line)
        # Join back to from list string
        updated_wg_config = "\n".join(updated_lines)
        #############################################################################
        # OR
        # CASE B: Static solution re-submitting WG configuration ####
        # interface_config = {
        #     "Address":
        #     f"{str(self.wg_server_ip)}/24",
        #     "ListenPort":
        #     "51820",
        #     "PrivateKey":
        #     self.private_key,
        #     "PostUp":
        #     "iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
        #     "PostDown":
        #     "iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE",
        # }
        # config_data = "[Interface]\n"
        # for key, value in interface_config.items():
        #     config_data += f"{key} = {value}\n"
        # updated_wg_config = config_data
        ###############################################################

        # Add new peers: [Peer] sections
        # Extend config string with peers
        # Mark start and stop of block for new service
        updated_wg_config += f'\n###START_BLOCK_{self.service_id}'
        peer: Peer
        for peer in self.wg_client_peers:
            self.logger.info("Peer received: %s", peer)
            updated_wg_config += f"\n[Peer] #{peer.name}\n"
            updated_wg_config += f"PublicKey = {peer.peer_public_key}\n"
            updated_wg_config += f"AllowedIPs = {peer.peer_overlay_ip}/32\n"
        updated_wg_config += f'###STOP_BLOCK_{self.service_id}\n'

        self.logger.info("Config object created: %s", updated_wg_config)

        self.config_wg_data = updated_wg_config
        # return config_data

    # Update DNSMasq config
    def update_dnsmasq_config(self):
        '''
        Update the DNSMasq config with a list of dictionaries containing hostname and assigned IP.

        Args:
            dns_list (list[Dict[str, str]]): A list where each item is a dictionary 
                                         containing 'hostname' and 'assigned_ip' as strings.
            Example:
            dns_list =  [
                            {"scomponent-ex1": "10.13.13.1"},
                            {"scomponent-ex2": "10.13.13.2"}
                        ]
        '''

        # CASE A: Dynamic, extend existing configuration,
        dnsmasq_config = k8s_shim.get_k8s_configmap_object(
            namespace=self.namespace,
            configmap_name=self.configmap_dnsmasq_name)

        #############################################################################
        # OR
        # CASE B: Static solution re-submitting WG configuration ####
        # dnsmasq_config = "server=8.8.8.8\n"
        # dnsmasq_config += "address=/example.com/10.0.0.1\n"
        dnsmasq_config += f'\n###START_BLOCK_{self.service_id}'
        for peer in self.wg_client_peers:
            dnsmasq_config += f"\naddress=/{peer.name}/{peer.peer_overlay_ip}\n"
        dnsmasq_config += f'###STOP_BLOCK_{self.service_id}\n'
        self.logger.info("Dnsmaq config object created: %s", dnsmasq_config)
        self.config_dnsmaq_data = dnsmasq_config

    def restart_wg_pod(self):
        '''
        Restart wireguard server pod using the updated configmap.
        All new peers client peers public keys and asigned IPs are registered.
        '''
        error_list = []
        success_wg = k8s_shim.create_k8s_configmap_object(
            namespace=self.namespace,
            configmap_name=self.configmap_wg_name,
            config_data=self.config_wg_data)
        if not success_wg:
            error_list.append(self.configmap_wg_name)
        success_dnsmasq = k8s_shim.create_k8s_configmap_object(
            namespace=self.namespace,
            configmap_name=self.configmap_dnsmasq_name,
            config_data=self.config_dnsmaq_data)
        if not success_dnsmasq:
            error_list.append(self.configmap_dnsmasq_name)
        success = success_wg and success_dnsmasq
        if not success:
            self.logger.info("Failed to update configmap with name: %s",
                             '-'.join(error_list))
            return False, "Failed to update ConfigMap"
        success = k8s_shim.restart_pod(namespace=self.namespace,
                                       pod_label=self.pod_label)
        if not success:
            self.logger.error("No WireGuard pod found with label: %s",
                              self.pod_label)
            return False, "No WireGuard pod found"
        return True, "Success"

    def reset_configmaps(self):
        """
        Set configmaps to intial values
        """
        #Reset masqdns configmap
        dnsmasq_config = "server=8.8.8.8\n"
        # dnsmasq_config += "address=/example.com/10.0.0.1\n"
        self.config_dnsmaq_data = dnsmasq_config
        # Reset wireguard configmap
        interface_config = {
            "Address": f"{str(self.wg_server_ip)}/24",
            "ListenPort": "51820",
            "PrivateKey": self.private_key,
            "PostUp":
            "iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
            "PostDown":
            "iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE",
        }
        config_data = "[Interface]\n"
        for key, value in interface_config.items():
            config_data += f"{key} = {value}\n"
        self.config_wg_data = config_data

    def remove_service_overlay_block(self) -> str:
        """
        Remove service related entries from
            wg_configmap
            dnsmaq_configmap
        Used when destroying a service deployment from the contunuum
        Args:
            configmap (str): The original ConfigMap as a string.

        Returns:
            str: The modified ConfigMap as a string.
        """
        wg_config = k8s_shim.get_k8s_configmap_object(
            namespace=self.namespace, configmap_name=self.configmap_wg_name)
        updated_wg_config = utils.remove_block_from_string(
            str_item=wg_config,
            start_str=f'###START_BLOCK_{self.service_id}',
            stop_str=f'###STOP_BLOCK_{self.service_id}')

        dnsmasq_config = k8s_shim.get_k8s_configmap_object(
            namespace=self.namespace,
            configmap_name=self.configmap_dnsmasq_name)
        updated_dnsmaq_config = utils.remove_block_from_string(
            str_item=dnsmasq_config,
            start_str=f'###START_BLOCK_{self.service_id}',
            stop_str=f'###STOP_BLOCK_{self.service_id}')
        self.config_wg_data = updated_wg_config
        self.config_dnsmaq_data = updated_dnsmaq_config


def setup_k8s_domain_wg(peers: list[Peer], service_id: str):
    '''
    Undertake all the process to configure and restart wg pod (wg, dnsmasq containers)
    Arg: 
            peers (List[Peer]): A list of Peer objects containing fields for
                             WireGuard and Dnsmaq configuration for each peer.
            Peer object:
             name: str
             peer_public_key: str
             peer_overlay_ip: str
    Retrun:
      Success (Boolean), Message (str) 
    '''
    wg_configurator = WgServerConfig(service_id=service_id, peers=peers)
    if not service_id:  # On reset
        wg_configurator.reset_configmaps()
    else:
        if peers:  # on create overlay
            if not wg_configurator.is_valid():
                return False, "Wireguard server peer is missing"
            wg_configurator.generate_wireguard_config()
            wg_configurator.update_dnsmasq_config()
        else:  # on destroy overlay
            wg_configurator.remove_service_overlay_block()
    return wg_configurator.restart_wg_pod()
