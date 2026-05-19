# protocol.py
# Contains header definitions (Frame, Packet, Segment) and layer class skeletons
# for Layer 2 (Data Link), Layer 3 (Network), and Layer 4 (Transport).

TYPE_IPV4 = 0x0800   # Ethernet type field value for IPv4
PROTO_UDP = 17       # IP protocol field value for UDP-like payload
SEG_DATA  = 0        # Transport segment type: DATA
SEG_ACK   = 1        # Transport segment type: ACK
MAX_DATA_SIZE = 500  # Maximum payload bytes per transport segment


# ---------------------------------------------------------------------------
# Layer 2 – Ethernet-like Frame
# ---------------------------------------------------------------------------

class Frame:
    """Data Link layer PDU.

    Fields (mirrors Ethernet header):
        dest_mac  – 6-byte destination MAC, e.g. 'BB:BB:BB:BB:BB:BB'
        src_mac   – 6-byte source MAC
        type      – 2-byte EtherType; 0x0800 = IPv4
        payload   – encapsulated Packet object
    """

    def __init__(self, dest_mac: str, src_mac: str, payload, etype: int = TYPE_IPV4):
        self.dest_mac = dest_mac
        self.src_mac  = src_mac
        self.type     = etype
        self.payload  = payload  # Packet

    def get_payload(self):
        return self.payload

    def __repr__(self):
        return (f"Frame(src={self.src_mac}, dst={self.dest_mac}, "
                f"type={hex(self.type)})")


# ---------------------------------------------------------------------------
# Layer 3 – IP-like Packet
# ---------------------------------------------------------------------------

class Packet:
    """Network layer PDU.

    Fields (mirrors IPv4 header subset):
        src_ip       – source IP string, e.g. '10.0.1.10'
        dest_ip      – destination IP string
        ttl          – time-to-live (decremented at each router; drop when 0)
        protocol     – 1 byte; 17 = UDP-like payload
        total_length – header + payload size in bytes
        payload      – encapsulated Segment object
    """

    HEADER_SIZE = 20  # fixed header overhead in bytes (simplified)

    def __init__(self, src_ip: str, dest_ip: str, ttl: int, payload : Segment,
                 protocol: int = PROTO_UDP):
        self.src_ip       = src_ip
        self.dest_ip      = dest_ip
        self.ttl          = ttl
        self.protocol     = protocol
        self.payload      = payload  # Segment
        self.total_length = self.HEADER_SIZE + payload.data

    def get_payload(self):
        return self.payload

    def __repr__(self):
        return (f"Packet(src={self.src_ip}, dst={self.dest_ip}, "
                f"ttl={self.ttl}, len={self.total_length})")


# ---------------------------------------------------------------------------
# Layer 4 – UDP-like Segment with rdt2.2 ACK support
# ---------------------------------------------------------------------------

class Segment:
    """Transport layer PDU.

    Fields:
        src_port        – source port number (2 bytes)
        dest_port       – destination port number (2 bytes)
        length          – total segment length in bytes (header + data)
        checksum        – computed checksum for error detection (2 bytes)
        type            – SEG_DATA (0) or SEG_ACK (1)
        sequence_number – alternating bit: 0 or 1
        data            – payload size in bytes (0 for ACK)
    """

    HEADER_SIZE = 10  # fixed header overhead: src_port+dest_port+len+cksum+type+seq

    def __init__(self, src_port: int, dest_port: int, fragment_flag: int,
                 seg_type: int, sequence_number: int,
                 data: int = 0, checksum: int = 0):
        self.src_port        = src_port
        self.dest_port       = dest_port
        self.type            = seg_type # 0 -> data; 1 -> ack
        self.sequence_number = sequence_number # alternating between 0 and 1
        self.data            = data
        self.fragment_flag   = fragment_flag # fragementation flag indicate same fragement or not
        self.length          = self.HEADER_SIZE + data
        self.checksum        = checksum  # filled in by TransportLayer.compute_checksum

    def get_data(self):
        return self.data

    def __repr__(self):
        kind = "DATA" if self.type == SEG_DATA else "ACK"
        return (f"Segment(type={kind}, seq={self.sequence_number}, "
                f"len={self.length}, cksum={self.checksum})")


# ---------------------------------------------------------------------------
# Layer 2 – Data Link Layer
# ---------------------------------------------------------------------------

class DataLinkLayer:
    """Handles framing, MAC addressing, learning, and local frame delivery.

    Each node (host or router interface) owns one DataLinkLayer instance.

    Attributes:
        node_name   – human-readable label used in log output (e.g. 'Host A')
        mac_address – this interface's own MAC address
        mac_table   – dict mapping next-hop IP → MAC address (ARP-like cache)
        network_layer – reference to the NetworkLayer above (set after init)
    """

    def __init__(self, node_name: str, mac_address: str, mac_table: dict[str, str], network_neighbour: dict[str, tuple["DataLinkLayer", str]] ):
        self.node_name     = node_name
        self.mac_address   = mac_address
        
        # from the config, it allow relation betwen ip and mac to be created
        self.mac_table = mac_table 
        
        self.interface_table  = {}
        
        self.network_layer : NetworkLayer | None = None  # injected after construction
        
        # pass in when creating object, provide a view of connected node, linking ip and its corresponding object  
        self.network_neighbour = network_neighbour
    # ------------------------------------------------------------------
    # Sending path (downward from Network Layer)
    # ------------------------------------------------------------------

    # call this 
    def receive_packet_from_network_layer(self, packet: Packet, next_hop_ip: str, outgoing_interface: str):
        """Accept a Packet from the Network Layer and transmit it as a Frame.

        Steps:
            1. Look up destination MAC for next_hop_ip.
            2. Create a Frame wrapping the packet.
            3. Send the frame onto the link.

        Args:
            packet      – the IP packet to encapsulate
            next_hop_ip – next-hop IP address to resolve to a MAC
        """
        # this function will be call to passing in data
        # all we care at L2 is how to pass data from host to router

        print(f"{self.node_name}: Layer 2: Packet received from Network Layer")

        # using the next hop ip from L3 find its mac address, as L2 use mac address
        dest_mac = self.mac_lookup(next_hop_ip)

        # create a frame data structue, where the dest mac is router, 
        # sending from current node so itself (node) mac address, 
        # the packet itself will be pass it as payload
        frame = self.create_frame(dest_mac, self.mac_address, packet)

        # find which object is going to transmiss to within the same network using the hardcoded interface 
        destination, interface = self.network_neighbour[outgoing_interface]

        # send to the router by call the router's L2 function
        self.send_frame(frame, destination, interface)
        pass

    def mac_lookup(self, next_hop_ip: str) -> str:
        """Return the MAC address for the given next-hop IP.

        Looks up self.mac_table; raises KeyError if not found.

        Args:
            next_hop_ip – IP address to resolve

        Returns:
            MAC address string
        """
        # return the result after using next hop ip to find it mac address
        return self.mac_table[next_hop_ip]
        pass

    def create_frame(self, dest_mac: str, src_mac: str, packet: Packet) -> Frame:
        """Wrap a Packet inside an Ethernet-like Frame.

        Args:
            dest_mac – destination MAC address
            src_mac  – source MAC address (this interface)
            packet   – payload to encapsulate

        Returns:
            A new Frame object
        """
        # return the create Frame data strcture
        return Frame(dest_mac, src_mac, packet)
        pass

    def send_frame(self, frame: Frame, destination : object, interface: str):
        """Transmit a Frame to the next node's DataLinkLayer.

        In this simulation 'sending' means calling destination.receive_frame().

        Args:
            frame       – the Frame to transmit
            destination – the receiving DataLinkLayer instance
        """
        print(f"{self.node_name}: Layer 2: Frame sent")
        # by passing in the dest (router) object, making the dest (router) object to call received, making passing possible
        destination.receive_frame(frame, interface)
        pass

    # ------------------------------------------------------------------
    # Receiving path (upward from the link / toward Network Layer)
    # ------------------------------------------------------------------
    
    # call this one
    def receive_frame(self, frame: Frame, interface: str = ""):
        """Process an incoming Frame.

        Steps:
            1. Log receipt.
            2. Learn the source MAC address.
            3. Deliver the payload up to the Network Layer.

        Args:
            frame     – the received Frame
            interface – label of the interface it arrived on (for routers)
        """
        print(f"{self.node_name}: Layer 2: Frame received"
              + (f" on {interface}" if interface else ""))

        # check the dest mac is matching node's mac address
        if frame.dest_mac != self.mac_address:
            print('wrong mac address')
            return 
        
        # building the relation between src mac and the interface
        self.mac_learning(frame.src_mac, interface)
        
        # passing the frame payload up
        self.send_up_to_network_layer(frame.payload)
        pass

    def mac_learning(self, src_mac: str, interface: str = ""):
        """Record the source MAC → interface mapping in mac_table.

        Args:
            src_mac   – source MAC address extracted from the received frame
            interface – interface label (informational)
        """
        print(f"{self.node_name}: Layer 2: Source MAC learned: {src_mac}"
              + (f" on {interface}" if interface else ""))

        # learning and mapping the relationship between src ac address and the interface
        self.interface_table[src_mac] = interface
        pass

    def send_up_to_network_layer(self, packet: Packet):
        """Deliver the decapsulated Packet to the Network Layer.

        Args:
            packet – the IP packet extracted from the frame payload
        """
        print(f"{self.node_name}: Layer 2: Packet delivered to Network Layer")

        # by passing the payload from the frame, passing the informatin up to L3
        self.network_layer.receive_packet_from_data_link_layer(packet)
        pass


# ---------------------------------------------------------------------------
# Layer 3 – Network Layer
# ---------------------------------------------------------------------------

class NetworkLayer:
    """Handles IP addressing, routing, TTL management, and packet forwarding.

    Each node owns one NetworkLayer instance.

    Attributes:
        node_name      – label for logging
        ip_addresses   – list of IP addresses assigned to this node's interfaces
        routing_table  – list of route dicts:
                           {'network': '10.0.2.0/24',
                            'interface': 'eth1',
                            'next_hop': '10.0.2.20'}
        data_link_layers – dict mapping interface label → DataLinkLayer instance
        transport_layer  – reference to the TransportLayer above (hosts only)
    """

    DEFAULT_TTL = 4

    def __init__(self, node_name: str, ip_addresses: list[str],
                 routing_table: list[dict]):
        self.node_name       = node_name
        self.ip_addresses    = ip_addresses
        self.routing_table   = routing_table
        self.data_link_layers: dict[str, DataLinkLayer] = {}
        self.transport_layer : TransportLayer | None = None  # injected after construction

    # ------------------------------------------------------------------
    # Sending path (downward from Transport Layer)
    # ------------------------------------------------------------------

    def receive_segment_from_transport_layer(self, segment: Segment,
                                              src_ip: str, dest_ip: str):
        """Accept a Segment from the Transport Layer and forward it as a Packet.

        Steps:
            1. Create an IP Packet wrapping the segment.
            2. Perform routing table lookup.
            3. Pass packet down to the Data Link Layer.

        Args:
            segment – the transport segment to encapsulate
            src_ip  – source IP for the packet header
            dest_ip – destination IP for the packet header
        """
        print(f"{self.node_name}: Layer 3: Segment received from Transport Layer: "
              f"SRC_IP={src_ip}, DST_IP={dest_ip}, TTL={self.DEFAULT_TTL}")
        new_packet = self.create_packet(src_ip, dest_ip, segment)
        table = self.routing_table_lookup(dest_ip)
        self.send_down_to_data_link_layer(new_packet, table["interface"], table["next_hop"])
        pass

    def create_packet(self, src_ip: str, dest_ip: str, segment: Segment,
                      ttl: int = None) -> Packet:
        """Build an IP Packet encapsulating the given Segment.

        Args:
            src_ip  – source IP address
            dest_ip – destination IP address
            segment – payload segment
            ttl     – time-to-live (defaults to DEFAULT_TTL)

        Returns:
            A new Packet object
        """
        return Packet(src_ip, dest_ip, ttl or self.DEFAULT_TTL, segment)

    def routing_table_lookup(self, dest_ip: str) -> dict:
        """Find the best route for dest_ip in self.routing_table.

        Performs longest-prefix match. Returns the matching route dict
        containing 'interface' and 'next_hop' keys.

        Args:
            dest_ip – destination IP address string

        Returns:
            Route dict, e.g. {'network': '10.0.2.0/24',
                               'interface': 'eth1', 'next_hop': '10.0.2.20'}

        Raises:
            ValueError if no matching route is found.
        """

        def _ip_to_int(ip: str) -> int:
            parts = ip.split('.')
            result = 0
            for part in parts:
                result = (result << 8) | int(part)
            return result

        print(f"{self.node_name}: Layer 3: Routing table lookup performed")
        dest_int = _ip_to_int(dest_ip)
        best_match = None
        best_prefix_len = -1

        for route in self.routing_table:
            network_ip, prefix_len = route["network"].split('/')
            prefix_len = int(prefix_len)

            # build mask from prefix length, e.g. /24 -> 0xFFFFFF00
            if prefix_len == 0:
                mask = 0
            else:
                mask = ((1 << 32) - 1) ^ ((1 << (32 - prefix_len)) - 1)

            network_int = _ip_to_int(network_ip)

            if dest_int & mask == network_int:
                if prefix_len > best_prefix_len:
                    best_prefix_len = prefix_len
                    best_match = route

        if best_match is None:
            raise ValueError(f"No matching route found for {dest_ip}")

        return best_match
        pass

    def send_down_to_data_link_layer(self, packet: Packet,
                                      interface: str, next_hop_ip: str):
        """Hand the Packet to the appropriate Data Link Layer for transmission.

        Args:
            packet      – the IP packet to send
            interface   – outgoing interface label
            next_hop_ip – next-hop IP address for MAC resolution
        """
        print(f"{self.node_name}: Layer 3: Packet forwarded to Data Link Layer")
        self.data_link_layers[interface].receive_packet_from_network_layer(packet, next_hop_ip, interface)
        pass

    # ------------------------------------------------------------------
    # Receiving / forwarding path (upward from Data Link Layer)
    # ------------------------------------------------------------------

    def receive_packet_from_data_link_layer(self, packet: Packet):
        """Process a Packet arriving from the Data Link Layer.

        For hosts: if dest_ip matches a local IP, deliver to Transport Layer.
        For routers: decrement TTL then re-route (forward_packet).

        Args:
            packet – the received IP packet
        """
        print(f"{self.node_name}: Layer 3: Packet received from Data Link Layer: "
              f"SRC_IP={packet.src_ip}, DST_IP={packet.dest_ip}, TTL={packet.ttl}")
        if self.is_local_delivery(packet.dest_ip):
            self.send_up_to_transport_layer(packet.get_payload())
        else:
            packet.ttl -= 1
            self.forward_packet(packet)
        pass

    def forward_packet(self, packet: Packet):
        """Route and forward a transit packet (router behaviour).

        Steps:
            1. Decrement TTL; drop and log if TTL reaches 0.
            2. Perform routing table lookup.
            3. Send down to the selected Data Link Layer.

        Args:
            packet – the IP packet to forward
        """
        if packet.ttl <= 0:
            return
        table = self.routing_table_lookup(packet.dest_ip)
        next_hop = table["next_hop"] if table["next_hop"] is not None else packet.dest_ip
        self.send_down_to_data_link_layer(packet, table["interface"], next_hop)
        pass

    def is_local_delivery(self, dest_ip: str) -> bool:
        """Return True if dest_ip belongs to one of this node's interfaces.

        Args:
            dest_ip – destination IP to check

        Returns:
            bool
        """
        for ip in self.ip_addresses:
            if ip == dest_ip:
                return True
        return False

    def send_up_to_transport_layer(self, segment: Segment):
        """Deliver the decapsulated Segment to the Transport Layer.

        Args:
            segment – the transport segment extracted from the packet payload
        """
        print(f"{self.node_name}: Layer 3: Segment delivered to Transport Layer")
        self.transport_layer.receive_segment_from_network_layer(segment)


# ---------------------------------------------------------------------------
# Layer 4 – Transport Layer  (rdt2.2 – Alternating Bit Protocol)
# ---------------------------------------------------------------------------

class TransportLayer:
    """Handles segmentation, checksums, port-based delivery, and rdt2.2.

    rdt2.2 (Alternating Bit Protocol):
        - Sender alternates sequence numbers 0 → 1 → 0 → …
        - Sender waits for ACK with the correct sequence number before advancing.
        - On wrong/corrupt ACK the sender retransmits the current segment.
        - Receiver sends ACK matching the received sequence number.
        - On corrupt or duplicate segment the receiver resends the last ACK.

    Attributes:
        node_name      – label for logging
        src_port       – source port number
        dest_port      – destination port number
        src_ip         – this host's IP (used when building packets)
        dest_ip        – peer host's IP
        seq_num        – current sender sequence number (0 or 1)
        last_ack_sent  – last ACK sequence number sent (receiver side)
        network_layer  – reference to the NetworkLayer below
    """

    def __init__(self, node_name: str, src_port: int, dest_port: int,
                 src_ip: str, dest_ip: str):
        self.node_name     = node_name
        self.src_port      = src_port
        self.dest_port     = dest_port
        self.src_ip        = src_ip
        self.dest_ip       = dest_ip
        self.remaining_data = None
        self.backup_sent_data_segment = None
        self.segment_type  = 0 
        self.sequence_number = 0   # alternating bit between 0 and 1
        self.last_ack_sent = 0  # last ACK seq sent by receiver, init with 0
        self.expected_sequence_number = 0 
        self.network_layer : NetworkLayer | None = None  # injected after construction

    
    # ------------------------------------------------------------------
    # Sending path (downward from Application Layer)
    # ------------------------------------------------------------------

    def send_data_segment(self, application_data: int):
        """Reliably send one data chunk using rdt2.2.

        Creates a DATA segment, computes its checksum, sends it down, then
        waits for the correct ACK.  Retransmits on wrong or corrupt ACK.

        Args:
            application_data – payload size in bytes (≤ MAX_DATA_SIZE per segment)
        """
        fragment_flag, data, self.remaining_data = self.fragmentation(application_data)
            
        checksum = self.compute_checksum(data)
        segment_created = self.create_segment(SEG_DATA, self.sequence_number, fragment_flag, checksum, data)
        self.backup_sent_data_segment = segment_created
        self.send_segment_to_network_layer(segment_created)
        pass

    def fragmentation(self, data: int) -> tuple[int, int, int | None]:
        """Split data size into a sendable chunk and optional remainder.

        Args:
            data – total payload size in bytes
        """
        print(f"{self.node_name}: Layer 4: Data received from Application Layer. "
              f"Data size={data}")
        # TODO: split data into chunks <= MAX_DATA_SIZE, call _send_segment for each
        is_fragment = 1
        is_not_fragment = 0
        if data > MAX_DATA_SIZE:
            remaining = data - MAX_DATA_SIZE
            return is_fragment, int(MAX_DATA_SIZE), remaining
        else:
            return is_not_fragment, data, None
        pass

    def compute_checksum(self, data: int) -> int:
        """Compute a simple checksum over the segment data.

        Args:
            data – payload size in bytes

        Returns:
            Integer checksum value (0–65535)
        """
        print(f"{self.node_name}: Layer 4: Checksum computed")
        # TODO: return sum(ord(c) for c in data) % 65536
        return (31 * data) % 65536
        pass

    def create_segment(self, segment_type :int, sequence_number: int, fragment_flag: int, 
                       checksum: int, data: int = 0) -> Segment:
        """Build a Segment with the given parameters.

        Args:
            seg_type  – SEG_DATA or SEG_ACK
            seq_num   – sequence number (0 or 1)
            data      – payload size in bytes (0 for ACK)
            checksum  – pre-computed checksum value

        Returns:
            A new Segment object
        """

        return Segment(self.src_port, self.dest_port, fragment_flag,
                       segment_type, sequence_number, data, checksum)
        pass

    def send_segment_to_network_layer(self, segment: Segment):
        """Pass a Segment down to the Network Layer for transmission.

        Args:
            segment – the segment to send
        """
        print(f"{self.node_name}: Layer 4: Segment sent to Network Layer")
        self.network_layer.receive_segment_from_transport_layer(segment, self.src_ip, self.dest_ip)
        
        # # updating sequence number
        # self.sequence_number = self.sequence_number + 1
        # if self.sequence_number > 1:
        #     self.sequence_number = 0
        # pass

    # ------------------------------------------------------------------
    # Receiving path (upward from Network Layer)
    # ------------------------------------------------------------------

    def receive_segment_from_network_layer(self, segment: Segment):
        """Handle an incoming Segment from the Network Layer.

        DATA segment:
            1. Verify checksum; discard on failure and resend last ACK.
            2. Check sequence number; discard duplicates and resend last ACK.
            3. Deliver data to application layer.
            4. Send ACK with the same sequence number.

        ACK segment (sender side):
            1. Verify checksum.
            2. Check if ACK matches the current expected sequence number.

        Args:
            segment – the received segment
        """
        print(f"{self.node_name}: Layer 4: Segment received from Network Layer")
        # work depending on segmnet.type

        # received data
        if segment.type == SEG_DATA:
            if self.verify_checksum(segment):
                # expecting same sequence number first
                if self.expected_sequence_number == segment.sequence_number:
                    self.deliver_to_application(segment.data)
                    self._send_ack_segment(self.expected_sequence_number)

                    # updateing the expect sequence number
                    self.expected_sequence_number = self.expected_sequence_number + 1
                    if self.expected_sequence_number > 1:
                        self.expected_sequence_number = 0
                # duplicate handling 
                else:
                    self._send_ack_segment(self.last_ack_sent)       
            # checksum incorrect, request retransmission
            else:
                self._send_ack_segment(self.last_ack_sent)



        # received ack
        else: # segment.type == SEG_ACK
            if self.verify_checksum(segment):
                # expecting same sequence number first
                if self.sequence_number == segment.sequence_number:
                    print(f"ACK received: seq={self.sequence_number}")

                    # updateing the expect sequence number
                    self.sequence_number = self.sequence_number + 1
                    if self.sequence_number > 1:
                        self.sequence_number = 0
                    
                    # send next segment if fragmentation still have reminding data
                    if self.remaining_data is not None: 
                        # data transmission
                        self.send_data_segment(self.remaining_data)
                    # if no reminding data do nothing
                else:
                    # if different, must be the last sent segment need to resend
                    self.send_segment_to_network_layer(self.backup_sent_data_segment)
            else:
                # checksum incorrect, request retransmission
                self.send_segment_to_network_layer(self.backup_sent_data_segment)

        pass

    def verify_checksum(self, segment: Segment) -> bool:
        """Verify the checksum of a received segment.

        Args:
            segment – the segment to verify

        Returns:
            True if checksum is valid, False otherwise
        """
        print(f"{self.node_name}: Layer 4: Checksum verified")
        if segment.checksum == self.compute_checksum(segment.data):
            return True
        return False
        pass

    def _send_ack_segment(self, sequence_number: int):
        """Create and send an ACK segment for the given sequence number.

        Args:
            seq_num – sequence number to acknowledge
        """
        print(f"{self.node_name}: Layer 4: ACK sent: seq={sequence_number}")
        fragment_flag = 0
        checksum = self.compute_checksum(0)
        data = 0
        segment_type = SEG_ACK
        segment = self.create_segment(segment_type, sequence_number, fragment_flag, checksum, data)
        self.send_segment_to_network_layer(segment)
        # update the last ack value
        self.last_ack_sent = segment.sequence_number
        pass

    def deliver_to_application(self, data: int):
        """Deliver received data to the application layer (print / return).

        Args:
            data – the application message payload
        """
        print(f"{self.node_name}: Layer 4: DATA segment delivered to Application Layer. "
              f"Data size={data}")
        pass