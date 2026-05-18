from config import host_a, host_b, router_R1
from protocol import *




class Host:
    def __init__(self, host_name: str, host_sender: object, host_receiver: object, router_interface: object, interface: str, src_port: int, dest_port: int):
        # creating the link between router and its corresponding interface
        self.host_connect_router_interface = {}
        self.data_link_layer = DataLinkLayer(host_name, host_sender.mac, host_sender.mac_table, self.host_connect_router_interface)
        # connecting between data link layer
        self.host_connect_router_interface["eth0"] = (router_interface, interface) # host a -> interface 1; host b -> interface 2
        self.data_link_layer.network_layer = self.network_layer # connecting layer
        
        # network layer
        self.network_layer =  NetworkLayer(host_name, [host_sender.ip], host_sender.routing_table)
        # connecting between data link and network
        self.network_layer.data_link_layers["eth0"] = self.data_link_layer
        self.network_layer.transport_layer = self.transport_layer

        # transport layer
        self.transport_layer = TransportLayer(host_name, src_port, dest_port, host_sender.ip, host_receiver.ip)
        self.transport_layer.network_layer = self.network_layer
    
    def input(self):
        pass
     
class Router:
    def __init__(self, router_name: str, host_a_data_link: object, host_b_data_link: object):
        
        # Create Data link Layer for Router R1
        self.router_interface_connect_host = {}
        self.router_interface_connect_host["interface_1"] = (host_a_data_link, "eth0")
        self.data_link_layer_interface_1 = DataLinkLayer("interface1",router_R1.interfaces["interface_1"].mac,router_R1.mac_table,router_interface_1_connect_host_a)
        self.router_interface_connect_host["interface_2"] = (host_b_data_link, "eth0")
        self.data_link_layer_interface_2 =  DataLinkLayer("interface2",router_R1.interfaces["interface_2"].mac,router_R1.mac_table,router_interface_2_connect_host_b)
        
        # Create Network Layer for Router R1
        self.router_R1_ip_addresses = [router_R1.interfaces["interface_1"].ip, router_R1.interfaces["interface_2"].ip]
        self.network_layer = NetworkLayer(router_name, self.router_R1_ip_addresses, router_R1.routing_table)

        self.network_layer.data_link_layers["interface_1"] = self.data_link_layer_interface_1
        self.network_layer.data_link_layers["interface_2"] = self.data_link_layer_interface_2
        
        # Router data link layers need to reference the router's own network layer
        self.data_link_layer_interface_1.network_layer = self.network_layer
        self.data_link_layer_interface_2.network_layer = self.network_layer    


    



# creating the link between router and its corresponding interface
host_a_connect_router_interface_1 = {}
host_b_connect_router_interface_2 = {}
router_interface_1_connect_host_a = {}
router_interface_2_connect_host_b = {}

# create data link layer
host_a_data_link = DataLinkLayer("HostA", host_a.mac, host_a.mac_table,host_a_connect_router_interface_1)

host_b_data_link = DataLinkLayer("HostB", host_b.mac, host_b.mac_table,host_b_connect_router_interface_2)

router_R1_data_link_interface_1 = DataLinkLayer("interface1",router_R1.interfaces["interface_1"].mac,router_R1.mac_table,router_interface_1_connect_host_a)
router_R1_data_link_interface_2 = DataLinkLayer("interface2",router_R1.interfaces["interface_2"].mac,router_R1.mac_table,router_interface_2_connect_host_b)

# connecting between data link layer
host_a_connect_router_interface_1["eth0"] = (router_R1_data_link_interface_1, "interface_1")
host_b_connect_router_interface_2["eth0"] = (router_R1_data_link_interface_2, "interface_2")
router_interface_1_connect_host_a["interface_1"] = (host_a_data_link, "eth0")
router_interface_2_connect_host_b["interface_2"] = (host_b_data_link, "eth0")

# connecting between each data link and network
host_a_network_layer = NetworkLayer("HostA", [host_a.ip], host_a.routing_table)
host_b_network_layer = NetworkLayer("HostB", [host_b.ip], host_b.routing_table)

host_a_network_layer.data_link_layers["eth0"] = host_a_data_link
host_b_network_layer.data_link_layers["eth0"] = host_b_data_link

# Create Network Layer for Router R1
router_R1_ip_addresses = [router_R1.interfaces["interface_1"].ip, router_R1.interfaces["interface_2"].ip]
router_network_layer = NetworkLayer("RouterR1", router_R1_ip_addresses, router_R1.routing_table)

router_network_layer.data_link_layers["interface_1"] = router_R1_data_link_interface_1
router_network_layer.data_link_layers["interface_2"] = router_R1_data_link_interface_2

host_a_data_link.network_layer = host_a_network_layer
host_b_data_link.network_layer = host_b_network_layer

# Router data link layers need to reference the router's own network layer
router_R1_data_link_interface_1.network_layer = router_network_layer
router_R1_data_link_interface_2.network_layer = router_network_layer

# Create Transport Layer
# Hosts
host_a_transport_layer = TransportLayer("HostA", 1234, 5678, host_a.ip, host_b.ip)
host_a_transport_layer.network_layer = host_a_network_layer


host_b_transport_layer = TransportLayer("HostB", 5678, 1234, host_b.ip, host_a.ip)
host_b_transport_layer.network_layer = host_b_network_layer

# Routers

# Connect Transport Layer
host_a_network_layer.transport_layer = host_a_transport_layer
host_b_network_layer.transport_layer = host_b_transport_layer


