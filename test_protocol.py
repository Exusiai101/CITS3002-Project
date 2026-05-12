import unittest
from unittest.mock import MagicMock

from protocol import (
    Frame, Packet, Segment,
    DataLinkLayer, NetworkLayer, TransportLayer,
    TYPE_IPV4, PROTO_UDP, SEG_DATA, SEG_ACK, MAX_DATA_SIZE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_segment(data="hello", seq=0, seg_type=SEG_DATA):
    return Segment(src_port=1234, dest_port=5678,
                   seg_type=seg_type, sequence_number=seq, data=data)


def make_packet(dest_ip="10.0.2.20", src_ip="10.0.1.10", ttl=4):
    return Packet(src_ip=src_ip, dest_ip=dest_ip, ttl=ttl, payload=make_segment())


# ---------------------------------------------------------------------------
# Constants
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
        self.seg = make_segment(data="hello")
        self.pkt = Packet("10.0.1.10", "10.0.2.20", ttl=4, payload=self.seg)

    def test_fields_set_on_init(self):
        self.assertEqual(self.pkt.src_ip, "10.0.1.10")
        self.assertEqual(self.pkt.dest_ip, "10.0.2.20")
        self.assertEqual(self.pkt.ttl, 4)
        self.assertEqual(self.pkt.protocol, PROTO_UDP)
        self.assertIs(self.pkt.payload, self.seg)

    def test_total_length_is_header_plus_data(self):
        self.assertEqual(self.pkt.total_length, Packet.HEADER_SIZE + len("hello"))

    def test_total_length_with_empty_segment(self):
        empty_seg = Segment(1, 2, SEG_ACK, 0, data="")
        pkt = Packet("10.0.1.10", "10.0.2.20", ttl=4, payload=empty_seg)
        self.assertEqual(pkt.total_length, Packet.HEADER_SIZE)

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
        seg = Segment(1234, 5678, SEG_DATA, 0, "hello", checksum=42)
        self.assertEqual(seg.src_port, 1234)
        self.assertEqual(seg.dest_port, 5678)
        self.assertEqual(seg.type, SEG_DATA)
        self.assertEqual(seg.sequence_number, 0)
        self.assertEqual(seg.data, "hello")
        self.assertEqual(seg.checksum, 42)

    def test_ack_segment_fields(self):
        ack = Segment(1234, 5678, SEG_ACK, 1, data="")
        self.assertEqual(ack.type, SEG_ACK)
        self.assertEqual(ack.sequence_number, 1)
        self.assertEqual(ack.data, "")

    def test_length_is_header_plus_data(self):
        seg = Segment(1, 2, SEG_DATA, 0, data="hello")
        self.assertEqual(seg.length, Segment.HEADER_SIZE + len("hello"))

    def test_ack_length_is_header_only(self):
        ack = Segment(1, 2, SEG_ACK, 1, data="")
        self.assertEqual(ack.length, Segment.HEADER_SIZE)

    def test_get_data(self):
        seg = Segment(1, 2, SEG_DATA, 0, data="world")
        self.assertEqual(seg.get_data(), "world")

    def test_repr_data_segment_shows_DATA(self):
        seg = Segment(1, 2, SEG_DATA, 0, data="hi")
        self.assertIn("DATA", repr(seg))

    def test_repr_ack_segment_shows_ACK(self):
        ack = Segment(1, 2, SEG_ACK, 1, data="")
        self.assertIn("ACK", repr(ack))

    def test_sequence_number_stored(self):
        seg0 = Segment(1, 2, SEG_DATA, 0, "a")
        seg1 = Segment(1, 2, SEG_DATA, 1, "b")
        self.assertEqual(seg0.sequence_number, 0)
        self.assertEqual(seg1.sequence_number, 1)


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
        seg = make_segment()
        pkt = self.nl.create_packet("10.0.1.10", "10.0.2.20", seg)
        self.assertIsInstance(pkt, Packet)
        self.assertEqual(pkt.src_ip, "10.0.1.10")
        self.assertEqual(pkt.dest_ip, "10.0.2.20")
        self.assertIs(pkt.payload, seg)

    def test_create_packet_uses_default_ttl_when_none(self):
        pkt = self.nl.create_packet("10.0.1.10", "10.0.2.20", make_segment())
        self.assertEqual(pkt.ttl, NetworkLayer.DEFAULT_TTL)

    def test_create_packet_uses_custom_ttl(self):
        pkt = self.nl.create_packet("10.0.1.10", "10.0.2.20", make_segment(), ttl=2)
        self.assertEqual(pkt.ttl, 2)

    # --- routing_table_lookup ---

    def test_routing_table_lookup_matches_host_in_subnet(self):
        # 10.0.2.20 belongs to 10.0.2.0/24
        route = self.nl.routing_table_lookup("10.0.2.20")
        self.assertEqual(route["interface"], "eth0")
        self.assertEqual(route["next_hop"], "10.0.1.1")

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
        dl.receive_packet_from_network_layer.assert_called_once_with(pkt, "10.0.1.1")

    def test_send_up_calls_transport_layer(self):
        self.nl.transport_layer = MagicMock()
        seg = make_segment()
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

    def test_initial_seq_num_is_zero(self):
        self.assertEqual(self.tl.seq_num, 0)

    def test_initial_last_ack_sent_is_minus_one(self):
        self.assertEqual(self.tl.last_ack_sent, -1)

    def test_network_layer_starts_none(self):
        self.assertIsNone(self.tl.network_layer)

    # --- compute_checksum ---

    def test_compute_checksum_sum_of_ascii_mod_65536(self):
        result = self.tl.compute_checksum("hello")
        expected = sum(ord(c) for c in "hello") % 65536
        self.assertEqual(result, expected)

    def test_compute_checksum_empty_string_is_zero(self):
        self.assertEqual(self.tl.compute_checksum(""), 0)

    # --- verify_checksum ---

    def test_verify_checksum_accepts_valid_segment(self):
        data = "hello"
        cksum = sum(ord(c) for c in data) % 65536
        seg = Segment(1234, 5678, SEG_DATA, 0, data, checksum=cksum)
        self.assertTrue(self.tl.verify_checksum(seg))

    def test_verify_checksum_rejects_corrupt_segment(self):
        seg = Segment(1234, 5678, SEG_DATA, 0, "hello", checksum=9999)
        self.assertFalse(self.tl.verify_checksum(seg))

    # --- create_segment ---

    def test_create_segment_data_type(self):
        seg = self.tl.create_segment(SEG_DATA, seq_num=0, data="hello", checksum=42)
        self.assertIsInstance(seg, Segment)
        self.assertEqual(seg.src_port, 1234)
        self.assertEqual(seg.dest_port, 5678)
        self.assertEqual(seg.type, SEG_DATA)
        self.assertEqual(seg.sequence_number, 0)
        self.assertEqual(seg.data, "hello")
        self.assertEqual(seg.checksum, 42)

    def test_create_segment_ack_type(self):
        ack = self.tl.create_segment(SEG_ACK, seq_num=1)
        self.assertIsInstance(ack, Segment)
        self.assertEqual(ack.type, SEG_ACK)
        self.assertEqual(ack.sequence_number, 1)
        self.assertEqual(ack.data, "")

    # --- send_segment_to_network_layer ---

    def test_send_segment_passes_to_network_layer(self):
        self.tl.network_layer = MagicMock()
        seg = make_segment()
        self.tl.send_segment_to_network_layer(seg)
        self.tl.network_layer.receive_segment_from_transport_layer.assert_called_once_with(
            seg, "10.0.1.10", "10.0.2.20"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)