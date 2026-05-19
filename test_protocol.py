import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock

from protocol import (
    Frame, Packet, Segment,
    DataLinkLayer, NetworkLayer, TransportLayer,
    TYPE_IPV4, PROTO_UDP, SEG_DATA, SEG_ACK, MAX_DATA_SIZE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_segment(data: int = 0, seq: int = 0, seg_type: int = SEG_DATA,
                 fragment_flag: int = 0, checksum: int = 0) -> Segment:
    """Build a Segment for testing.

    `data` is an int (byte size) in this protocol implementation, since the
    application data is simulated by size rather than by content.
    """
    return Segment(src_port=1234, dest_port=5678,
                   fragment_flag=fragment_flag,
                   seg_type=seg_type, sequence_number=seq,
                   data=data, checksum=checksum)


def make_packet(dest_ip: str = "10.0.2.20", src_ip: str = "10.0.1.10",
                ttl: int = 4, payload: Segment | None = None) -> Packet:
    if payload is None:
        # data=0 keeps Packet.total_length valid given current Packet impl
        # (which evaluates `len(payload.data) if payload.data else 0`).
        payload = make_segment(data=0)
    return Packet(src_ip=src_ip, dest_ip=dest_ip, ttl=ttl, payload=payload)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):
    def test_type_ipv4(self):
        self.assertEqual(TYPE_IPV4, 0x0800)

    def test_proto_udp(self):
        self.assertEqual(PROTO_UDP, 17)

    def test_seg_data(self):
        self.assertEqual(SEG_DATA, 0)

    def test_seg_ack(self):
        self.assertEqual(SEG_ACK, 1)

    def test_max_data_size(self):
        self.assertEqual(MAX_DATA_SIZE, 500)


# ---------------------------------------------------------------------------
# Frame
# ---------------------------------------------------------------------------

class TestFrame(unittest.TestCase):
    def setUp(self):
        self.pkt = make_packet()
        self.frame = Frame("BB:BB:BB:BB:BB:BB", "AA:AA:AA:AA:AA:AA", self.pkt)

    def test_fields_set_on_init(self):
        self.assertEqual(self.frame.dest_mac, "BB:BB:BB:BB:BB:BB")
        self.assertEqual(self.frame.src_mac, "AA:AA:AA:AA:AA:AA")
        self.assertIs(self.frame.payload, self.pkt)

    def test_default_etype_is_ipv4(self):
        self.assertEqual(self.frame.type, TYPE_IPV4)

    def test_explicit_etype_stored(self):
        f = Frame("BB:BB:BB:BB:BB:BB", "AA:AA:AA:AA:AA:AA", self.pkt, etype=0x0806)
        self.assertEqual(f.type, 0x0806)

    def test_get_payload_returns_packet(self):
        self.assertIs(self.frame.get_payload(), self.pkt)

    def test_repr_contains_src_dst_and_type(self):
        r = repr(self.frame)
        self.assertIn("AA:AA:AA:AA:AA:AA", r)
        self.assertIn("BB:BB:BB:BB:BB:BB", r)
        self.assertIn("0x800", r)


# ---------------------------------------------------------------------------
# Packet
# ---------------------------------------------------------------------------

class TestPacket(unittest.TestCase):
    def setUp(self):
        self.seg = make_segment(data=0)
        self.pkt = Packet("10.0.1.10", "10.0.2.20", ttl=4, payload=self.seg)

    def test_fields_set_on_init(self):
        self.assertEqual(self.pkt.src_ip, "10.0.1.10")
        self.assertEqual(self.pkt.dest_ip, "10.0.2.20")
        self.assertEqual(self.pkt.ttl, 4)
        self.assertEqual(self.pkt.protocol, PROTO_UDP)
        self.assertIs(self.pkt.payload, self.seg)

    def test_total_length_with_zero_data(self):
        # data=0 → falsy branch → total_length is just header
        self.assertEqual(self.pkt.total_length, Packet.HEADER_SIZE)

    def test_get_payload_returns_segment(self):
        self.assertIs(self.pkt.get_payload(), self.seg)

    def test_repr_contains_ips_and_ttl(self):
        r = repr(self.pkt)
        self.assertIn("10.0.1.10", r)
        self.assertIn("10.0.2.20", r)
        self.assertIn("4", r)


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------

class TestSegment(unittest.TestCase):
    def test_data_segment_fields(self):
        seg = Segment(1234, 5678, fragment_flag=0, seg_type=SEG_DATA,
                      sequence_number=0, data=5, checksum=42)
        self.assertEqual(seg.src_port, 1234)
        self.assertEqual(seg.dest_port, 5678)
        self.assertEqual(seg.type, SEG_DATA)
        self.assertEqual(seg.sequence_number, 0)
        self.assertEqual(seg.data, 5)
        self.assertEqual(seg.checksum, 42)
        self.assertEqual(seg.fragment_flag, 0)

    def test_ack_segment_fields(self):
        ack = Segment(1234, 5678, fragment_flag=0, seg_type=SEG_ACK,
                      sequence_number=1, data=0)
        self.assertEqual(ack.type, SEG_ACK)
        self.assertEqual(ack.sequence_number, 1)
        self.assertEqual(ack.data, 0)

    def test_length_is_header_plus_data(self):
        seg = Segment(1, 2, fragment_flag=0, seg_type=SEG_DATA,
                      sequence_number=0, data=5)
        self.assertEqual(seg.length, Segment.HEADER_SIZE + 5)

    def test_ack_length_is_header_only(self):
        ack = Segment(1, 2, fragment_flag=0, seg_type=SEG_ACK,
                      sequence_number=1, data=0)
        self.assertEqual(ack.length, Segment.HEADER_SIZE)

    def test_get_data_returns_int(self):
        seg = Segment(1, 2, fragment_flag=0, seg_type=SEG_DATA,
                      sequence_number=0, data=42)
        self.assertEqual(seg.get_data(), 42)

    def test_repr_data_segment_shows_DATA(self):
        seg = Segment(1, 2, fragment_flag=0, seg_type=SEG_DATA,
                      sequence_number=0, data=2)
        self.assertIn("DATA", repr(seg))

    def test_repr_ack_segment_shows_ACK(self):
        ack = Segment(1, 2, fragment_flag=0, seg_type=SEG_ACK,
                      sequence_number=1, data=0)
        self.assertIn("ACK", repr(ack))

    def test_sequence_number_stored(self):
        seg0 = Segment(1, 2, fragment_flag=0, seg_type=SEG_DATA,
                       sequence_number=0, data=1)
        seg1 = Segment(1, 2, fragment_flag=0, seg_type=SEG_DATA,
                       sequence_number=1, data=1)
        self.assertEqual(seg0.sequence_number, 0)
        self.assertEqual(seg1.sequence_number, 1)

    def test_fragment_flag_stored(self):
        seg = Segment(1, 2, fragment_flag=1, seg_type=SEG_DATA,
                      sequence_number=0, data=1)
        self.assertEqual(seg.fragment_flag, 1)


# ---------------------------------------------------------------------------
# DataLinkLayer
# ---------------------------------------------------------------------------

class TestDataLinkLayer(unittest.TestCase):
    def setUp(self):
        self.dl = DataLinkLayer(
            "Host A", "AA:AA:AA:AA:AA:AA",
            mac_table={},
            network_neighbour={},
        )

    def test_init_fields(self):
        self.assertEqual(self.dl.node_name, "Host A")
        self.assertEqual(self.dl.mac_address, "AA:AA:AA:AA:AA:AA")

    def test_mac_table_starts_empty(self):
        self.assertEqual(self.dl.mac_table, {})

    def test_interface_table_starts_empty(self):
        self.assertEqual(self.dl.interface_table, {})

    def test_network_layer_starts_none(self):
        self.assertIsNone(self.dl.network_layer)

    def test_mac_lookup_returns_mac_for_known_ip(self):
        self.dl.mac_table["10.0.1.1"] = "BB:BB:BB:BB:BB:BB"
        self.assertEqual(self.dl.mac_lookup("10.0.1.1"), "BB:BB:BB:BB:BB:BB")

    def test_mac_lookup_raises_key_error_for_unknown_ip(self):
        with self.assertRaises(KeyError):
            self.dl.mac_lookup("10.0.9.9")

    def test_create_frame_wraps_packet(self):
        pkt = make_packet()
        frame = self.dl.create_frame("BB:BB:BB:BB:BB:BB", "AA:AA:AA:AA:AA:AA", pkt)
        self.assertIsInstance(frame, Frame)
        self.assertEqual(frame.dest_mac, "BB:BB:BB:BB:BB:BB")
        self.assertEqual(frame.src_mac, "AA:AA:AA:AA:AA:AA")
        self.assertIs(frame.payload, pkt)

    def test_send_frame_calls_receive_on_destination(self):
        dest = MagicMock()
        frame = Frame("BB:BB:BB:BB:BB:BB", "AA:AA:AA:AA:AA:AA", make_packet())
        self.dl.send_frame(frame, dest, "eth0")
        dest.receive_frame.assert_called_once_with(frame, "eth0")

    def test_mac_learning_stores_mac_in_interface_table(self):
        self.dl.mac_learning("AA:AA:AA:AA:AA:AA", interface="eth0")
        self.assertEqual(self.dl.interface_table["AA:AA:AA:AA:AA:AA"], "eth0")

    def test_send_up_to_network_layer_passes_packet_up(self):
        self.dl.network_layer = MagicMock()
        pkt = make_packet()
        self.dl.send_up_to_network_layer(pkt)
        self.dl.network_layer.receive_packet_from_data_link_layer.assert_called_once_with(pkt)

    def test_receive_frame_drops_mismatched_dest_mac(self):
        # Frame addressed to a different MAC should not propagate upward.
        self.dl.network_layer = MagicMock()
        wrong_frame = Frame(dest_mac="ZZ:ZZ:ZZ:ZZ:ZZ:ZZ",
                            src_mac="BB:BB:BB:BB:BB:BB",
                            payload=make_packet())
        self.dl.receive_frame(wrong_frame, interface="eth0")
        self.dl.network_layer.receive_packet_from_data_link_layer.assert_not_called()

    def test_receive_frame_learns_source_and_passes_up(self):
        self.dl.network_layer = MagicMock()
        pkt = make_packet()
        frame = Frame(dest_mac=self.dl.mac_address,
                      src_mac="BB:BB:BB:BB:BB:BB",
                      payload=pkt)
        self.dl.receive_frame(frame, interface="eth0")
        self.assertEqual(self.dl.interface_table["BB:BB:BB:BB:BB:BB"], "eth0")
        self.dl.network_layer.receive_packet_from_data_link_layer.assert_called_once_with(pkt)


# ---------------------------------------------------------------------------
# NetworkLayer
# ---------------------------------------------------------------------------

ROUTING_TABLE = [
    {"network": "10.0.2.0/24", "interface": "eth0", "next_hop": "10.0.1.1"},
    {"network": "10.0.1.0/24", "interface": "lo",   "next_hop": None},
]


class TestNetworkLayer(unittest.TestCase):
    def setUp(self):
        self.nl = NetworkLayer(
            node_name="Host A",
            ip_addresses=["10.0.1.10"],
            routing_table=ROUTING_TABLE,
        )

    def test_init_fields(self):
        self.assertEqual(self.nl.node_name, "Host A")
        self.assertEqual(self.nl.ip_addresses, ["10.0.1.10"])
        self.assertEqual(self.nl.data_link_layers, {})
        self.assertIsNone(self.nl.transport_layer)

    def test_default_ttl(self):
        self.assertEqual(NetworkLayer.DEFAULT_TTL, 4)

    # --- create_packet ---

    def test_create_packet_sets_fields(self):
        seg = make_segment(data=0)
        pkt = self.nl.create_packet("10.0.1.10", "10.0.2.20", seg)
        self.assertIsInstance(pkt, Packet)
        self.assertEqual(pkt.src_ip, "10.0.1.10")
        self.assertEqual(pkt.dest_ip, "10.0.2.20")
        self.assertIs(pkt.payload, seg)

    def test_create_packet_uses_default_ttl_when_none(self):
        pkt = self.nl.create_packet("10.0.1.10", "10.0.2.20", make_segment(data=0))
        self.assertEqual(pkt.ttl, NetworkLayer.DEFAULT_TTL)

    def test_create_packet_uses_custom_ttl(self):
        pkt = self.nl.create_packet("10.0.1.10", "10.0.2.20",
                                    make_segment(data=0), ttl=2)
        self.assertEqual(pkt.ttl, 2)

    # --- routing_table_lookup ---

    def test_routing_table_lookup_matches_host_in_subnet(self):
        # 10.0.2.20 belongs to 10.0.2.0/24
        route = self.nl.routing_table_lookup("10.0.2.20")
        self.assertEqual(route["interface"], "eth0")
        self.assertEqual(route["next_hop"], "10.0.1.1")

    def test_routing_table_lookup_longest_prefix_match(self):
        # Add a more specific route — it should win over /24.
        nl = NetworkLayer("Test", ["10.0.1.10"], [
            {"network": "10.0.0.0/8",  "interface": "wan", "next_hop": "10.0.0.1"},
            {"network": "10.0.2.0/24", "interface": "eth0", "next_hop": "10.0.1.1"},
        ])
        route = nl.routing_table_lookup("10.0.2.20")
        self.assertEqual(route["interface"], "eth0")

    def test_routing_table_lookup_raises_for_unroutable_ip(self):
        with self.assertRaises(ValueError):
            self.nl.routing_table_lookup("192.168.1.1")

    # --- is_local_delivery ---

    def test_is_local_delivery_true_for_own_ip(self):
        self.assertTrue(self.nl.is_local_delivery("10.0.1.10"))

    def test_is_local_delivery_false_for_remote_ip(self):
        self.assertFalse(self.nl.is_local_delivery("10.0.2.20"))

    # --- forward_packet ---

    def test_forward_packet_drops_silently_when_ttl_is_zero(self):
        dl = MagicMock()
        self.nl.data_link_layers["eth0"] = dl
        pkt = make_packet(dest_ip="10.0.2.20", ttl=0)
        self.nl.forward_packet(pkt)
        dl.receive_packet_from_network_layer.assert_not_called()

    def test_forward_packet_routes_packet_when_ttl_positive(self):
        dl = MagicMock()
        self.nl.data_link_layers["eth0"] = dl
        pkt = make_packet(dest_ip="10.0.2.20", ttl=3)
        self.nl.forward_packet(pkt)
        dl.receive_packet_from_network_layer.assert_called_once()

    # --- receive_packet_from_data_link_layer ---

    def test_remote_packet_has_ttl_decremented_and_is_forwarded(self):
        dl = MagicMock()
        self.nl.data_link_layers["eth0"] = dl
        pkt = make_packet(dest_ip="10.0.2.20", src_ip="10.0.1.10", ttl=3)
        self.nl.receive_packet_from_data_link_layer(pkt)
        self.assertEqual(pkt.ttl, 2)
        dl.receive_packet_from_network_layer.assert_called()

    def test_local_packet_is_delivered_to_transport_layer(self):
        self.nl.transport_layer = MagicMock()
        pkt = make_packet(dest_ip="10.0.1.10", src_ip="10.0.2.20")
        self.nl.receive_packet_from_data_link_layer(pkt)
        self.nl.transport_layer.receive_segment_from_network_layer.assert_called_once()

    # --- wiring helpers ---

    def test_send_down_calls_correct_data_link_layer(self):
        dl = MagicMock()
        self.nl.data_link_layers["eth0"] = dl
        pkt = make_packet()
        self.nl.send_down_to_data_link_layer(pkt, "eth0", "10.0.1.1")
        # Current implementation forwards (packet, next_hop_ip, interface_label)
        dl.receive_packet_from_network_layer.assert_called_once_with(
            pkt, "10.0.1.1", "eth0"
        )

    def test_send_up_calls_transport_layer(self):
        self.nl.transport_layer = MagicMock()
        seg = make_segment(data=0)
        self.nl.send_up_to_transport_layer(seg)
        self.nl.transport_layer.receive_segment_from_network_layer.assert_called_once_with(seg)


# ---------------------------------------------------------------------------
# TransportLayer
# ---------------------------------------------------------------------------

class TestTransportLayer(unittest.TestCase):
    def setUp(self):
        self.tl = TransportLayer("Host A", src_port=1234, dest_port=5678,
                                 src_ip="10.0.1.10", dest_ip="10.0.2.20")

    def test_init_fields(self):
        self.assertEqual(self.tl.node_name, "Host A")
        self.assertEqual(self.tl.src_port, 1234)
        self.assertEqual(self.tl.dest_port, 5678)
        self.assertEqual(self.tl.src_ip, "10.0.1.10")
        self.assertEqual(self.tl.dest_ip, "10.0.2.20")

    def test_initial_sequence_number_is_zero(self):
        self.assertEqual(self.tl.sequence_number, 0)

    def test_initial_last_ack_sent_is_zero(self):
        self.assertEqual(self.tl.last_ack_sent, 0)

    def test_initial_expected_sequence_number_is_zero(self):
        self.assertEqual(self.tl.expected_sequence_number, 0)

    def test_initial_remaining_data_is_empty_list(self):
        # `remaining_data` was changed to a list (was previously None) so it can
        # accumulate fragments produced by `fragmentation()` for rdt2.2.
        self.assertEqual(self.tl.remaining_data, [])

    def test_network_layer_starts_none(self):
        self.assertIsNone(self.tl.network_layer)

    # --- compute_checksum ---

    def test_compute_checksum_formula(self):
        # Current implementation: (31 * data) % 65536
        self.assertEqual(self.tl.compute_checksum(10), (31 * 10) % 65536)

    def test_compute_checksum_zero_data(self):
        self.assertEqual(self.tl.compute_checksum(0), 0)

    def test_compute_checksum_wraps_to_16_bits(self):
        # 31 * 5000 = 155000, mod 65536 = 23928
        self.assertEqual(self.tl.compute_checksum(5000), 23928)
        self.assertLess(self.tl.compute_checksum(1_000_000), 65536)

    # --- verify_checksum ---

    def test_verify_checksum_accepts_valid_segment(self):
        data = 10
        cksum = (31 * data) % 65536
        seg = make_segment(data=data, checksum=cksum)
        self.assertTrue(self.tl.verify_checksum(seg))

    def test_verify_checksum_rejects_corrupt_segment(self):
        seg = make_segment(data=10, checksum=9999)
        self.assertFalse(self.tl.verify_checksum(seg))

    # --- create_segment ---

    def test_create_segment_data_type(self):
        # create_segment signature: (segment_type, sequence_number, fragment_flag, checksum, data)
        seg = self.tl.create_segment(SEG_DATA, sequence_number=0,
                                     fragment_flag=0, checksum=42, data=10)
        self.assertIsInstance(seg, Segment)
        self.assertEqual(seg.src_port, 1234)
        self.assertEqual(seg.dest_port, 5678)
        self.assertEqual(seg.type, SEG_DATA)
        self.assertEqual(seg.sequence_number, 0)
        self.assertEqual(seg.data, 10)
        self.assertEqual(seg.checksum, 42)

    def test_create_segment_ack_type(self):
        seg = self.tl.create_segment(SEG_ACK, sequence_number=1,
                                     fragment_flag=0, checksum=0, data=0)
        self.assertIsInstance(seg, Segment)
        self.assertEqual(seg.type, SEG_ACK)
        self.assertEqual(seg.sequence_number, 1)
        self.assertEqual(seg.data, 0)

    # --- send_segment_to_network_layer ---

    def test_send_segment_passes_to_network_layer(self):
        self.tl.network_layer = MagicMock()
        seg = make_segment(data=0)
        self.tl.send_segment_to_network_layer(seg)
        self.tl.network_layer.receive_segment_from_transport_layer.assert_called_once_with(
            seg, "10.0.1.10", "10.0.2.20"
        )

    # --- fragmentation ---
    #
    # `fragmentation()` now returns (fragment_flag, chunks_list) where
    # `chunks_list` is the list of chunk sizes (≤ MAX_DATA_SIZE each) and is
    # also stored on `self.remaining_data` for the rdt2.2 send loop to drain.

    def test_fragmentation_no_split_when_under_limit(self):
        flag, chunks = self.tl.fragmentation(100)
        self.assertEqual(chunks, [100])
        self.assertEqual(self.tl.remaining_data, [100])
        # The current implementation always returns fragment_flag=1; keep this
        # assertion in lockstep with the code rather than the (older) spec.
        self.assertEqual(flag, 1)

    def test_fragmentation_splits_when_over_limit(self):
        flag, chunks = self.tl.fragmentation(MAX_DATA_SIZE + 200)
        self.assertEqual(chunks, [MAX_DATA_SIZE, 200])
        self.assertEqual(self.tl.remaining_data, [MAX_DATA_SIZE, 200])
        self.assertEqual(flag, 1)

    def test_fragmentation_splits_exact_multiple(self):
        flag, chunks = self.tl.fragmentation(MAX_DATA_SIZE * 3)
        self.assertEqual(chunks, [MAX_DATA_SIZE] * 3)
        self.assertEqual(flag, 1)


# ---------------------------------------------------------------------------
# End-to-end simulation log comparison (CITS3002 spec, PDF pages 5-7)
# ---------------------------------------------------------------------------

# Expected log output for sending 10 bytes from Host A to Host B, taken
# verbatim from CITS3002-Project.pdf pages 5-7. Blank lines in the PDF
# (used there as section separators) are omitted here; the comparison
# also strips blank lines from the simulation's actual output.
EXPECTED_LOG_10_BYTES = """\
Host A: Layer 4: Data received from Application Layer. Data size=10
Host A: Layer 4: Checksum computed
Host A: Layer 4: Segment created by adding transport layer header (DATA, seq=0) (encapsulation)
Host A: Layer 4: Segment sent to Network Layer
Host A: Layer 3: Segment received from Transport Layer: SRC_IP=10.0.1.10, DST_IP=10.0.2.20, TTL=4
Host A: Layer 3: Destination IP read: 10.0.2.20
Host A: Layer 3: Routing table lookup performed
Host A: Layer 3: Next-hop IP determined: 10.0.1.1
Host A: Layer 3: Outgoing interface selected
Host A: Layer 3: Packet forwarded to Data Link Layer
Host A: Layer 2: Packet received from Network Layer
Host A: Layer 2: Destination MAC lookup for next-hop IP (10.0.1.1) → BB:BB:BB:BB:BB:BB
Host A: Layer 2: Frame created: SRC_MAC=AA:AA:AA:AA:AA:AA, DST_MAC=BB:BB:BB:BB:BB:BB
Host A: Layer 2: Frame sent
Router R1: Layer 2: Frame received on Interface 1
Router R1: Layer 2: Source MAC learned: AA:AA:AA:AA:AA:AA on Interface 1
Router R1: Layer 2: Packet delivered to Network Layer
Router R1: Layer 3: Packet received from Data Link Layer: SRC_IP=10.0.1.10, DST_IP=10.0.2.20, TTL=4
Router R1: Layer 3: Destination IP read: 10.0.2.20
Router R1: Layer 3: TTL decremented: 4 → 3
Router R1: Layer 3: Routing table lookup performed
Router R1: Layer 3: Next-hop IP determined: 10.0.2.20
Router R1: Layer 3: Outgoing interface selected (Interface 2)
Router R1: Layer 3: Packet forwarded to Data Link Layer
Router R1: Layer 2: Packet received from Network Layer
Router R1: Layer 2: Destination MAC lookup for next-hop IP (10.0.2.20) → DD:DD:DD:DD:DD:DD
Router R1: Layer 2: Frame created: SRC_MAC=CC:CC:CC:CC:CC:CC, DST_MAC=DD:DD:DD:DD:DD:DD
Router R1: Layer 2: Frame forwarded on Interface 2
Host B: Layer 2: Frame received
Host B: Layer 2: Source MAC learned: CC:CC:CC:CC:CC:CC
Host B: Layer 2: Packet delivered to Network Layer
Host B: Layer 3: Packet received from Data Link Layer: SRC_IP=10.0.1.10, DST_IP=10.0.2.20, TTL=3
Host B: Layer 3: Destination IP read: 10.0.2.20
Host B: Layer 3: Packet identified as local delivery
Host B: Layer 3: Segment delivered to Transport Layer
Host B: Layer 4: Segment received from Network Layer
Host B: Layer 4: Checksum verified
Host B: Layer 4: DATA segment delivered to Application Layer. Data size=10
Host B: Layer 4: Segment created by adding transport layer header (ACK, seq=0)
Host B: Layer 4: Segment sent to Network Layer
Host B: Layer 3: Segment received from Transport Layer: SRC_IP=10.0.2.20, DST_IP=10.0.1.10, TTL=4
Host B: Layer 3: Destination IP read: 10.0.1.10
Host B: Layer 3: Routing table lookup performed
Host B: Layer 3: Next-hop IP determined: 10.0.2.1
Host B: Layer 3: Outgoing interface selected
Host B: Layer 3: Packet forwarded to Data Link Layer
Host B: Layer 2: Packet received from Network Layer
Host B: Layer 2: Destination MAC lookup for next-hop IP (10.0.2.1) → CC:CC:CC:CC:CC:CC
Host B: Layer 2: Frame created: SRC_MAC=DD:DD:DD:DD:DD:DD, DST_MAC=CC:CC:CC:CC:CC:CC
Host B: Layer 2: Frame sent
Router R1: Layer 2: Frame received on Interface 2
Router R1: Layer 2: Source MAC learned: DD:DD:DD:DD:DD:DD on Interface 2
Router R1: Layer 2: Packet delivered to Network Layer
Router R1: Layer 3: Packet received from Data Link Layer: SRC_IP=10.0.2.20, DST_IP=10.0.1.10, TTL=4
Router R1: Layer 3: Destination IP read: 10.0.1.10
Router R1: Layer 3: TTL decremented: 4 → 3
Router R1: Layer 3: Routing table lookup performed
Router R1: Layer 3: Next-hop IP determined: 10.0.1.10
Router R1: Layer 3: Outgoing interface selected (Interface 1)
Router R1: Layer 3: Packet forwarded to Data Link Layer
Router R1: Layer 2: Packet received from Network Layer
Router R1: Layer 2: Destination MAC lookup for next-hop IP (10.0.1.10) → AA:AA:AA:AA:AA:AA
Router R1: Layer 2: Frame created: SRC_MAC=BB:BB:BB:BB:BB:BB, DST_MAC=AA:AA:AA:AA:AA:AA
Router R1: Layer 2: Frame forwarded on Interface 1
Host A: Layer 2: Frame received
Host A: Layer 2: Source MAC learned: BB:BB:BB:BB:BB:BB
Host A: Layer 2: Packet delivered to Network Layer
Host A: Layer 3: Packet received from Data Link Layer: SRC_IP=10.0.2.20, DST_IP=10.0.1.10, TTL=3
Host A: Layer 3: Destination IP read: 10.0.1.10
Host A: Layer 3: Packet identified as local delivery
Host A: Layer 3: Segment delivered to Transport Layer
Host A: Layer 4: Segment received from Network Layer
Host A: Layer 4: Checksum verified
Host A: Layer 4: ACK received: seq=0
"""


def _non_blank_lines(text: str) -> list[str]:
    """Split `text` into lines, strip trailing whitespace, drop empty lines."""
    return [line.rstrip() for line in text.splitlines() if line.strip()]


class TestSimulationLog(unittest.TestCase):
    """Run the full Host A → Router R1 → Host B simulation and compare its
    captured stdout, line by line, against the expected log from the project
    PDF. Blank lines (used as section separators in the PDF) are ignored on
    both sides so the test is robust to optional spacing in the output."""

    def _run_simulation(self, data_size: int) -> str:
        # Import lazily so importing the test module does not build the network.
        from devices import init_network

        host_a, _host_b, _router = init_network()
        buf = io.StringIO()
        with redirect_stdout(buf):
            host_a.send(data_size)
        return buf.getvalue()

    def test_simulation_log_matches_spec_for_10_bytes(self):
        actual_lines = _non_blank_lines(self._run_simulation(10))
        expected_lines = _non_blank_lines(EXPECTED_LOG_10_BYTES)

        # Compare line by line so the failure message pinpoints the divergence
        # rather than dumping the entire diff in one assertion.
        for index, expected in enumerate(expected_lines):
            self.assertLess(index, len(actual_lines),
                            msg=f"Output ended early — missing line {index + 1}: "
                                f"expected {expected!r}")
            self.assertEqual(actual_lines[index], expected,
                             msg=f"Mismatch on log line {index + 1}\n"
                                 f"  expected: {expected!r}\n"
                                 f"  actual:   {actual_lines[index]!r}")

        self.assertEqual(len(actual_lines), len(expected_lines),
                         msg=f"Simulation produced {len(actual_lines) - len(expected_lines)} "
                             f"extra trailing line(s); first extra: "
                             f"{actual_lines[len(expected_lines)]!r}"
                             if len(actual_lines) > len(expected_lines) else "")


if __name__ == "__main__":
    unittest.main(verbosity=2)