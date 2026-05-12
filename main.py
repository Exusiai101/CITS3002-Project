from config import host_a, host_b, router_R1
from protocol import *

# creating the link between router and its corresponding interface
host_a_connect_router_interface_1 = {}
host_b_connect_router_interface_2 = {}
router_interface_1_connect_host_a = {}
router_interface_2_connect_host_b = {}

# create data link layer
host_a_data_link = DataLinkLayer("HostA", host_a["mac"], host_a["mac_table"],host_a_connect_router_interface_1)

host_b_data_link = DataLinkLayer("HostB", host_b["mac"], host_b["mac_table"],host_b_connect_router_interface_2)

router_R1_data_link_interface_1 = DataLinkLayer("interface1",router_R1["interfaces"]["interface_1"]["mac"],router_R1["mac_table"],router_interface_1_connect_host_a)
router_R1_data_link_interface_2 = DataLinkLayer("interface2",router_R1["interfaces"]["interface_2"]["mac"],router_R1["mac_table"],router_interface_2_connect_host_b)

# connecting between data link layer
host_a_connect_router_interface_1["eth0"] = (router_R1_data_link_interface_1, "interface_1")
host_b_connect_router_interface_2["eth0"] = (router_R1_data_link_interface_2, "interface_2")
router_interface_1_connect_host_a["interface_1"] = (host_a_data_link, "eth0")
router_interface_2_connect_host_b["interface_2"] = (host_b_data_link, "eth0")

# connecting between each data link and network
host_a_data_link.network_layer 
host_b_data_link.network_layer
    # different router share network layer for routing decision
router_R1_data_link_interface_1.network_layer
router_R1_data_link_interface_2.network_layer 

# L2 action
host_a_data_link.receive_packet_from_network_layer
router_R1_data_link_interface_1.receive_packet_from_network_layer

host_b_data_link.receive_packet_from_network_layer
router_R1_data_link_interface_2.receive_packet_from_network_layer
# end at here and the router have sent the data back to host a