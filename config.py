# host A
host_a = {
    
    "ip": "10.0.1.10",
    "mac": "AA:AA:AA:AA:AA:AA",
    
    "routing_table": {
        "10.0.2.0/24":{
            "next_hop": "10.0.1.1",
            "interface": "eth0"
        }
    },

    "mac_table":{"10.0.1.1": "BB:BB:BB:BB:BB:BB"} # find the mac address of next hop, using its ip address
}

# host B
host_b = {
   
    "ip": "10.0.2.20",
    "mac": "DD:DD:DD:DD:DD:DD",
    
    "routing_table": {
        "10.0.1.0/24":{
            "next_hop": "10.0.2.1",
            "interface": "eth0"
        }
    },

    "mac_table":{"10.0.2.1": "CC:CC:CC:CC:CC:CC"} # find the mac address of next hop, using its ip address
}


# router 
router_R1 = {
    
    "routing_table": {
        "10.0.1.0/24": {
            "next_hop": None,
            "interface": "interface_1"
        },

        "10.0.2.0/24":  {
            "next_hop": None,
            "interface": "interface_2"
        }
    },

    "interfaces" : {
        "interface_1" :{
            "ip": "10.0.1.1", 
            "mac": "BB:BB:BB:BB:BB:BB"
        },

        "interface_2" :{
            "ip": "10.0.2.1",
            "mac": "CC:CC:CC:CC:CC:CC"
        }
    },
    # find the mac address of next hop, using its ip address
    "mac_table" : {
        "10.0.1.10": "AA:AA:AA:AA:AA:AA",
        "10.0.2.20": "DD:DD:DD:DD:DD:DD"
    }
}

