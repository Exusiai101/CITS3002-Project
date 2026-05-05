# data structure
class frame:
    # for data link layer
    def __init__(self, dest_mac, src_mac, ip_type, payload):
        self.dest_mac = dest_mac
        self.src_mac = src_mac
        self.type = ip_type
        self.payload = payload
        pass

class packet:
    # for network layer
    def __init__(self, scr_ip, dest_ip, ttl, protocol, total_length, payload):
        self.scr_ip = scr_ip
        self.dest_ip = dest_ip
        self.ttl = ttl
        self.protocol = protocol
        self.total_length = total_length
        self.payload = payload
        pass

class segment: # not pipe line, 
    # for transport layer
    def __init__(self, src_port, dest_port, length, checksum, type, sequence_number, data):
        self.src_port = src_port
        self.dest_port = dest_port
        self.length = length
        self.checksum = checksum
        self.type = type
        self.sequence_number = sequence_number
        self.data = data
        pass

# method
class data_link_layer:
    
    # sending
    def receive_packet_from_L3():
        pass
    
    def mac_lookup(next_hop_ip): 
        #use ip of next hop to deduce the mac address by using 
        # return dict[next_hop_ip]
        pass

    def create_frame():
        pass

    def send_frame_to_router():
        pass

    # receiving
    def receive_frame_from_router():
        pass

    def mac_learning(): # storing the mac address into the ip dictionary
        pass

    # handling where should the frame go after receiving
    def forwarding():
        pass

    def passUp_to_L3():
        pass