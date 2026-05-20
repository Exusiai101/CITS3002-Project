from config import host_a, host_b, router_R1, HostConfig
from protocol import *


class Host:
    """Represents a network host with Transport, Network, and Data Link layers."""

    def __init__(self, host_name: str, host_sender: HostConfig, host_receiver: HostConfig,
                 router_interface: DataLinkLayer, interface: str, src_port: int, dest_port: int):
        # Dict passed by reference — populated below once router_interface is known.
        self.host_connect_router_interface: dict[str, tuple[DataLinkLayer, str]] = {}

        # --- Data Link Layer ---
        self.data_link_layer = DataLinkLayer(
            host_name, host_sender.mac, host_sender.mac_table,
            self.host_connect_router_interface
        )

        # It's hardcoded by design.
        self.host_connect_router_interface["eth0"] = (router_interface, interface)

        # --- Network Layer ---
        self.network_layer = NetworkLayer(host_name, [host_sender.ip], host_sender.routing_table)
        self.network_layer.data_link_layers["eth0"] = self.data_link_layer

        # --- Transport Layer ---
        self.transport_layer = TransportLayer(
            host_name, src_port, dest_port, host_sender.ip, host_receiver.ip
        )
        self.transport_layer.network_layer = self.network_layer

        # Wire cross-references now that all objects exist.
        self.data_link_layer.network_layer = self.network_layer
        self.network_layer.transport_layer = self.transport_layer

    def send(self, data_size: int):
        # sending data_size bytes from this host's transport layer.
        self.transport_layer.send_data_segment(data_size)


class Router:
    # router with two interfaces, each with its own data link layer.

    def __init__(self, router_name: str):
        # Neighbour dicts stored as instance vars so connect_hosts() can populate
        # them after Host objects are created (breaks the circular dependency).
        self.router_if1_neighbours: dict[str, tuple[DataLinkLayer, str]] = {}
        self.router_if2_neighbours: dict[str, tuple[DataLinkLayer, str]] = {}

        # --- Data Link Layers (one per interface) ---
        self.data_link_layer_interface_1 = DataLinkLayer(
            router_name,
            router_R1.interfaces["interface_1"].mac,
            router_R1.mac_table,
            self.router_if1_neighbours
        )
        self.data_link_layer_interface_2 = DataLinkLayer(
            router_name,
            router_R1.interfaces["interface_2"].mac,
            router_R1.mac_table,
            self.router_if2_neighbours
        )

        # --- Network Layer ---
        router_ips = [
            router_R1.interfaces["interface_1"].ip,
            router_R1.interfaces["interface_2"].ip
        ]
        self.network_layer = NetworkLayer(router_name, router_ips, router_R1.routing_table)
        self.network_layer.data_link_layers["interface_1"] = self.data_link_layer_interface_1
        self.network_layer.data_link_layers["interface_2"] = self.data_link_layer_interface_2

        # Wire Data Link Layers up to the shared Network Layer.
        self.data_link_layer_interface_1.network_layer = self.network_layer
        self.data_link_layer_interface_2.network_layer = self.network_layer

    def connect_hosts(self, host_a_dl: DataLinkLayer, host_b_dl: DataLinkLayer):
        
        # connecting the router interface with a host
        self.router_if1_neighbours["interface_1"] = (host_a_dl, "eth0")
        self.router_if2_neighbours["interface_2"] = (host_b_dl, "eth0")


def init_network() -> tuple[Host, Host, Router]:
    # encapsulates the construction of devices and handle the connection
    router = Router("Router R1")

    host_a_obj = Host(
        "Host A", host_a, host_b,
        router.data_link_layer_interface_1, "interface_1",
        src_port=7543, dest_port=80
    )
    host_b_obj = Host(
        "Host B", host_b, host_a,
        router.data_link_layer_interface_2, "interface_2",
        src_port=80, dest_port=7543
    )

    router.connect_hosts(host_a_obj.data_link_layer, host_b_obj.data_link_layer)

    return host_a_obj, host_b_obj, router