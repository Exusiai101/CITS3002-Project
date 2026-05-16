# Rewrite all the dict using class

class HostConfig:
    def __init__(self, ip: str, mac: str, routing_table: list[dict], mac_table: dict[str, str]):
        self.ip = ip
        self.mac = mac
        self.routing_table = routing_table
        self.mac_table = mac_table

class InterfaceConfig:
    def __init__(self, ip: str, mac: str):
        self.ip = ip
        self.mac = mac

class RouterConfig:
    def __init__(self, routing_table: list[dict], interfaces: dict[str, InterfaceConfig], mac_table: dict[str, str]):
        self.routing_table = routing_table
        self.interfaces = interfaces
        self.mac_table = mac_table

# host A
host_a = HostConfig(
    ip="10.0.1.10",
    mac="AA:AA:AA:AA:AA:AA",
    routing_table=[
        {
            "network": "10.0.2.0/24",
            "next_hop": "10.0.1.1",
            "interface": "eth0"
        }
    ],
    mac_table={"10.0.1.1": "BB:BB:BB:BB:BB:BB"} # find the mac address of next hop, using its ip address
)

# host B
host_b = HostConfig(
    ip="10.0.2.20",
    mac="DD:DD:DD:DD:DD:DD",
    routing_table=[
        {
            "network": "10.0.1.0/24",
            "next_hop": "10.0.2.1",
            "interface": "eth0"
        }
    ],
    mac_table={"10.0.2.1": "CC:CC:CC:CC:CC:CC"} # find the mac address of next hop, using its ip address
)

# router 
router_R1 = RouterConfig(
    routing_table=[
        {
            "network": "10.0.1.0/24",
            "next_hop": None,
            "interface": "interface_1"
        },
        {
            "network": "10.0.2.0/24",
            "next_hop": None,
            "interface": "interface_2"
        }
    ],
    interfaces={
        "interface_1": InterfaceConfig(ip="10.0.1.1", mac="BB:BB:BB:BB:BB:BB"),
        "interface_2": InterfaceConfig(ip="10.0.2.1", mac="CC:CC:CC:CC:CC:CC")
    },
    # find the mac address of next hop, using its ip address
    mac_table={
        "10.0.1.10": "AA:AA:AA:AA:AA:AA",
        "10.0.2.20": "DD:DD:DD:DD:DD:DD"
    }
)
