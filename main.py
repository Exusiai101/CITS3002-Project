from config import host_a, host_b, router_R1
from protocol import *

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


# Execute Simulation
if __name__ == "__main__":
    print("Starting Simulation...")
    
    # Send a fragmented payload (e.g., 1200 > MAX_DATA_SIZE) to test rdt2.2 and segmentation
    host_a_transport_layer.send_data_segment("1200")
    
    print("\nSimulation Complete.")