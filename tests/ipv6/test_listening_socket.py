"""
Test the behaviour of listening sockets.
"""
import logging
from socket import AF_INET, AF_INET6, IPPROTO_UDP, IPPROTO_TCP
from ipaddress import IPv6Address
import unittest
from unittest.mock import Mock

from dhcpkit.ipv6 import SERVER_PORT, All_DHCP_Relay_Agents_and_Servers, CLIENT_PORT
from dhcpkit.ipv6.exceptions import ListeningSocketError, InvalidPacketError
from dhcpkit.ipv6.listening_socket import ListeningSocket
from dhcpkit.ipv6.messages import RelayForwardMessage, UnknownMessage, RelayReplyMessage, Message
from dhcpkit.ipv6.options import InterfaceIdOption, RelayMessageOption
from tests.ipv6.messages.test_advertise_message import advertise_message, advertise_packet
from tests.ipv6.messages.test_relay_forward_message import relayed_solicit_packet, relayed_solicit_message
from tests.ipv6.messages.test_relay_reply_message import relayed_advertise_message, relayed_advertise_packet
from tests.ipv6.messages.test_solicit_message import solicit_packet, solicit_message


class MockSocket:
    """
    Mock-up of a network socket for unit testing
    """

    def __init__(self, family: int, proto: int, address: str, port: int, interface_id: int, file_no: int):
        """
        Construct a new mock socket
        """
        self.family = family
        self.proto = proto
        self.getsockname = Mock(return_value=(address, port, 0, interface_id))
        self.file_no = file_no

        self.incoming_queue = []
        self.outgoing_queue = []

        self.pretend_sendto_fails = False

    def fileno(self) -> int:
        """
        Return a fake file descriptor
        """
        return self.file_no

    def add_to_incoming_queue(self, packet: bytes, sender: tuple):
        """
        Add this packet to the "received" queue

        :param packet: The bytes of the packet
        :param sender: The sender of the packet
        :type sender: (str, int, int, int)
        """
        self.incoming_queue.append((packet, sender))

    def recvfrom(self, bufsize: int) -> (bytes, (str, int, int, int)):
        """
        Pretend that this message was "received"

        :param bufsize: Length to truncate the packet to
        :return:
        """
        packet, sender = self.incoming_queue.pop()
        return packet[:bufsize], sender

    def sendto(self, packet: bytes, sender: tuple):
        """
        Pretend that this message was "sent"

        :param packet: The bytes of the packet
        :param sender: The sender of the packet
        :type sender: (str, int, int, int)
        """
        if self.pretend_sendto_fails:
            # Oops, we lost a byte
            packet = packet[:-1]

        self.outgoing_queue.append((packet, sender))
        return len(packet)

    def read_from_outgoing_queue(self) -> (bytes, (str, int, int, int)):
        """
        Get the first packet that was "sent"

        :return: The packet and the destination
        """
        return self.outgoing_queue.pop()


class ListeningSocketTestCase(unittest.TestCase):
    def test_constructor_link_local(self):
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', link_local_socket, global_address=IPv6Address('2001:db8::1'))

        self.assertEqual(listening_socket.interface_name, 'eth0')
        self.assertEqual(listening_socket.interface_id, b'eth0')
        self.assertEqual(listening_socket.interface_index, 42)
        self.assertEqual(listening_socket.listen_socket, link_local_socket)
        self.assertEqual(listening_socket.listen_address, IPv6Address('fe80::1'))
        self.assertEqual(listening_socket.reply_socket, link_local_socket)
        self.assertEqual(listening_socket.reply_address, IPv6Address('fe80::1'))
        self.assertEqual(listening_socket.global_address, IPv6Address('2001:db8::1'))
        self.assertEqual(listening_socket.fileno(), 1608)

    def test_constructor_unicast(self):
        global_unicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', global_unicast_socket)

        self.assertEqual(listening_socket.interface_name, 'eth0')
        self.assertEqual(listening_socket.interface_id, b'eth0')
        self.assertEqual(listening_socket.interface_index, 42)
        self.assertEqual(listening_socket.listen_socket, global_unicast_socket)
        self.assertEqual(listening_socket.listen_address, IPv6Address('2001:db8::1'))
        self.assertEqual(listening_socket.reply_socket, global_unicast_socket)
        self.assertEqual(listening_socket.reply_address, IPv6Address('2001:db8::1'))
        self.assertEqual(listening_socket.global_address, IPv6Address('2001:db8::1'))
        self.assertEqual(listening_socket.fileno(), 1608)

    def test_constructor_multicast(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        self.assertEqual(listening_socket.interface_name, 'eth0')
        self.assertEqual(listening_socket.interface_id, b'eth0')
        self.assertEqual(listening_socket.interface_index, 42)
        self.assertEqual(listening_socket.listen_socket, multicast_socket)
        self.assertEqual(listening_socket.listen_address, IPv6Address(All_DHCP_Relay_Agents_and_Servers))
        self.assertEqual(listening_socket.reply_socket, link_local_socket)
        self.assertEqual(listening_socket.reply_address, IPv6Address('fe80::1'))
        self.assertEqual(listening_socket.global_address, IPv6Address('2001:db8::1'))
        self.assertEqual(listening_socket.fileno(), 1608)

    def test_bad_proto(self):
        good_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)
        bad_socket_family = MockSocket(AF_INET, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)
        bad_socket_proto = MockSocket(AF_INET6, IPPROTO_TCP, '2001:db8::1', SERVER_PORT, 42, 1608)

        with self.assertRaisesRegex(ListeningSocketError, r'IPv6 UDP socket'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', bad_socket_family, good_socket)

        with self.assertRaisesRegex(ListeningSocketError, r'IPv6 UDP socket'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', bad_socket_proto, good_socket)

        with self.assertRaisesRegex(ListeningSocketError, r'IPv6 UDP socket'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', good_socket, bad_socket_family)

        with self.assertRaisesRegex(ListeningSocketError, r'IPv6 UDP socket'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', good_socket, bad_socket_proto)

    def test_bad_port(self):
        good_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)
        bad_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', CLIENT_PORT, 42, 1608)

        with self.assertRaisesRegex(ListeningSocketError, r'port 547'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', bad_socket, good_socket)

        with self.assertRaisesRegex(ListeningSocketError, r'port 547'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', good_socket, bad_socket)

    def test_global_address_finding(self):
        global_unicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::2', SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)

        # Test explicit global address
        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', global_unicast_socket, global_address=IPv6Address('2001:db8::1'))
        self.assertEqual(listening_socket.global_address, IPv6Address('2001:db8::1'))

        # Test taking the listen socket address
        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', global_unicast_socket)
        self.assertEqual(listening_socket.global_address, IPv6Address('2001:db8::2'))

        # Test no global address found
        with self.assertRaisesRegex(ListeningSocketError, r'Cannot determine global address'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', multicast_socket, link_local_socket)

    def test_interface_mismatch(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 41, 1608)

        with self.assertRaisesRegex(ListeningSocketError, r'same interface'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', multicast_socket, link_local_socket)

    def test_wildcard_address(self):
        wildcard_socket = MockSocket(AF_INET6, IPPROTO_UDP, '::', SERVER_PORT, 42, 1608)
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)

        with self.assertRaisesRegex(ListeningSocketError, r'wildcard'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', wildcard_socket)

        with self.assertRaisesRegex(ListeningSocketError, r'wildcard'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', multicast_socket, wildcard_socket, global_address=IPv6Address('2001:db8::1'))

    def test_global_reply_address(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        global_unicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::2', SERVER_PORT, 42, 1608)

        with self.assertRaisesRegex(ListeningSocketError, r'need link-local reply socket'):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', multicast_socket, global_unicast_socket, global_address=IPv6Address('2001:db8::1'))

    def test_unwanted_reply_address(self):
        global_unicast_listen_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)
        global_unicast_reply_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::2', SERVER_PORT, 42, 1608)

        with self.assertRaisesRegex(ListeningSocketError, r"can't use separate reply socket"):
            # noinspection PyTypeChecker
            ListeningSocket('eth0', global_unicast_listen_socket, global_unicast_reply_socket)

    def test_receive_direct(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        multicast_socket.add_to_incoming_queue(solicit_packet, ('2001:db8::babe', 546, 0, 42))
        with self.assertLogs(level=logging.DEBUG) as logged:
            received_message = listening_socket.recv_request()

        self.assertIsInstance(received_message, RelayForwardMessage)
        self.assertEqual(received_message.hop_count, 0)
        self.assertEqual(received_message.link_address, IPv6Address('2001:db8::1'))
        self.assertEqual(received_message.peer_address, IPv6Address('2001:db8::babe'))
        self.assertEqual(received_message.get_option_of_type(InterfaceIdOption).interface_id, b'eth0')
        self.assertEqual(received_message.relayed_message, solicit_message)

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Received SolicitMessage')
        self.assertRegex(log_output, r'from 2001:db8::babe')

    def test_receive_relayed(self):
        global_unicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', global_unicast_socket)

        global_unicast_socket.add_to_incoming_queue(relayed_solicit_packet, ('2001:db8::babe', 546, 0, 42))
        with self.assertLogs(level=logging.DEBUG) as logged:
            received_message = listening_socket.recv_request()

        self.assertIsInstance(received_message, RelayForwardMessage)
        self.assertEqual(received_message.hop_count, 2)
        self.assertEqual(received_message.link_address, IPv6Address('2001:db8::1'))
        self.assertEqual(received_message.peer_address, IPv6Address('2001:db8::babe'))
        self.assertEqual(received_message.get_option_of_type(InterfaceIdOption).interface_id, b'eth0')
        self.assertEqual(received_message.relayed_message, relayed_solicit_message)

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Received SolicitMessage')
        self.assertRegex(log_output, r'from fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r'via Fa2/3 of relay 2001:db8::babe')

    def test_receive_relayed_with_unprintable_interface_id(self):
        global_unicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', global_unicast_socket)

        # Start with a clean parse and then change interface-id
        new_message = Message.parse(relayed_solicit_packet)[1]
        new_message.inner_relay_message.get_option_of_type(InterfaceIdOption).interface_id = b'\x80\x81\x82'

        global_unicast_socket.add_to_incoming_queue(bytes(new_message.save()), ('2001:db8::babe', 546, 0, 42))
        with self.assertLogs(level=logging.DEBUG) as logged:
            listening_socket.recv_request()

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Received SolicitMessage')
        self.assertRegex(log_output, r'from fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r"via b'\\x80\\x81\\x82' of relay 2001:db8::babe")

    def test_receive_relayed_without_interface_id(self):
        global_unicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, '2001:db8::1', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', global_unicast_socket)

        # Start with a clean parse and then remove interface-id
        new_message = Message.parse(relayed_solicit_packet)[1]
        interface_id_option = new_message.inner_relay_message.get_option_of_type(InterfaceIdOption)
        new_message.inner_relay_message.options.remove(interface_id_option)

        global_unicast_socket.add_to_incoming_queue(bytes(new_message.save()), ('2001:db8::babe', 546, 0, 42))
        with self.assertLogs(level=logging.DEBUG) as logged:
            listening_socket.recv_request()

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Received SolicitMessage')
        self.assertRegex(log_output, r'from fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r'via relay 2001:db8::babe')

    def test_receive_bad_message(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        multicast_socket.add_to_incoming_queue(b'\x01ThisIsNotAValidDHCPv6Message', ('2001:db8::babe', 546, 0, 42))
        with self.assertRaisesRegex(InvalidPacketError, r"Invalid packet from \('2001:db8::babe', 546, 0, 42\)"):
            listening_socket.recv_request()

    def test_receive_unknown_message_type(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        multicast_socket.add_to_incoming_queue(b'\xffThisIsNotAValidDHCPv6Message', ('2001:db8::babe', 546, 0, 42))
        received_message = listening_socket.recv_request()

        self.assertIsInstance(received_message, RelayForwardMessage)
        self.assertEqual(received_message.hop_count, 0)
        self.assertEqual(received_message.link_address, IPv6Address('2001:db8::1'))
        self.assertEqual(received_message.peer_address, IPv6Address('2001:db8::babe'))
        self.assertEqual(received_message.get_option_of_type(InterfaceIdOption).interface_id, b'eth0')
        self.assertIsInstance(received_message.relayed_message, UnknownMessage)
        self.assertEqual(received_message.relayed_message.message_type, 255)

    def test_send_direct(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                                 RelayMessageOption(relayed_message=advertise_message)
                                             ])

        with self.assertLogs(level=logging.DEBUG) as logged:
            success = listening_socket.send_reply(outgoing_message)
            self.assertTrue(success)

        # Nothing should be sent from a multicast socket
        with self.assertRaises(IndexError):
            multicast_socket.read_from_outgoing_queue()

        # It must be on the link local socket
        sent_packet, recipient = link_local_socket.read_from_outgoing_queue()
        self.assertEqual(sent_packet, advertise_packet)
        self.assertEqual(recipient, ('fe80::babe', CLIENT_PORT, 0, 42))

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Sent AdvertiseMessage')
        self.assertRegex(log_output, r'to fe80::babe')

    def test_failed_send_direct(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)
        link_local_socket.pretend_sendto_fails = True

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                                 RelayMessageOption(relayed_message=advertise_message)
                                             ])

        with self.assertLogs(level=logging.DEBUG) as logged:
            success = listening_socket.send_reply(outgoing_message)
            self.assertFalse(success)

        # Nothing should be sent from a multicast socket
        with self.assertRaises(IndexError):
            multicast_socket.read_from_outgoing_queue()

        # It must be on the link local socket
        sent_packet, recipient = link_local_socket.read_from_outgoing_queue()
        self.assertNotEqual(sent_packet, advertise_packet)

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'AdvertiseMessage')
        self.assertRegex(log_output, r'to fe80::babe')
        self.assertRegex(log_output, r'could not be sent')

    def test_send_relayed(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                                 RelayMessageOption(relayed_message=relayed_advertise_message)
                                             ])

        with self.assertLogs(level=logging.DEBUG) as logged:
            success = listening_socket.send_reply(outgoing_message)
            self.assertTrue(success)

        # Nothing should be sent from a multicast socket
        with self.assertRaises(IndexError):
            multicast_socket.read_from_outgoing_queue()

        # It must be on the link local socket
        sent_packet, recipient = link_local_socket.read_from_outgoing_queue()
        self.assertEqual(sent_packet, relayed_advertise_packet)
        self.assertEqual(recipient, ('fe80::babe', SERVER_PORT, 0, 42))

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Sent AdvertiseMessage')
        self.assertRegex(log_output, r'to fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r'via Fa2/3 of relay fe80::babe')

    def test_failed_send_relayed(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)
        link_local_socket.pretend_sendto_fails = True

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                                 RelayMessageOption(relayed_message=relayed_advertise_message)
                                             ])

        with self.assertLogs(level=logging.DEBUG) as logged:
            success = listening_socket.send_reply(outgoing_message)
            self.assertFalse(success)

        # Nothing should be sent from a multicast socket
        with self.assertRaises(IndexError):
            multicast_socket.read_from_outgoing_queue()

        # It must be on the link local socket
        sent_packet, recipient = link_local_socket.read_from_outgoing_queue()
        self.assertNotEqual(sent_packet, relayed_advertise_packet)

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'AdvertiseMessage')
        self.assertRegex(log_output, r'to fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r"via Fa2/3 of relay fe80::babe")

    def test_send_relayed_with_unprintable_interface_id(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        # Start with a clean parse and then change interface-id
        new_message = Message.parse(relayed_advertise_packet)[1]
        new_message.inner_relay_message.get_option_of_type(InterfaceIdOption).interface_id = b'\x80\x81\x82'

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                                 RelayMessageOption(relayed_message=new_message)
                                             ])

        with self.assertLogs(level=logging.DEBUG) as logged:
            listening_socket.send_reply(outgoing_message)

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Sent AdvertiseMessage')
        self.assertRegex(log_output, r'to fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r"via b'\\x80\\x81\\x82' of relay fe80::babe")

    def test_send_relayed_without_interface_id(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        # Start with a clean parse and then change interface-id
        new_message = Message.parse(relayed_advertise_packet)[1]
        interface_id_option = new_message.inner_relay_message.get_option_of_type(InterfaceIdOption)
        new_message.inner_relay_message.options.remove(interface_id_option)

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                                 RelayMessageOption(relayed_message=new_message)
                                             ])

        with self.assertLogs(level=logging.DEBUG) as logged:
            listening_socket.send_reply(outgoing_message)

        log_output = '\n'.join(logged.output)
        self.assertRegex(log_output, r'Sent AdvertiseMessage')
        self.assertRegex(log_output, r'to fe80::3631:c4ff:fe3c:b2f1')
        self.assertRegex(log_output, r"via relay fe80::babe")

    def test_send_unwrapped(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        with self.assertRaisesRegex(ValueError, r'has to be wrapped'):
            listening_socket.send_reply(advertise_message)

    def test_send_badly_wrapped(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        with self.assertRaisesRegex(ValueError, r'link-address does not match'):
            listening_socket.send_reply(relayed_advertise_message)

        # Fix the link-address so the test continues to the interface-id
        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8:ffff:1::1'))

        with self.assertRaisesRegex(ValueError, r'interface-id in the reply does not match'):
            listening_socket.send_reply(relayed_advertise_message)

    def test_send_empty_wrapper(self):
        multicast_socket = MockSocket(AF_INET6, IPPROTO_UDP, All_DHCP_Relay_Agents_and_Servers, SERVER_PORT, 42, 1608)
        link_local_socket = MockSocket(AF_INET6, IPPROTO_UDP, 'fe80::1%eth0', SERVER_PORT, 42, 1608)

        # noinspection PyTypeChecker
        listening_socket = ListeningSocket('eth0', multicast_socket, link_local_socket,
                                           global_address=IPv6Address('2001:db8::1'))

        outgoing_message = RelayReplyMessage(hop_count=0,
                                             link_address=IPv6Address('2001:db8::1'),
                                             peer_address=IPv6Address('fe80::babe'),
                                             options=[
                                                 InterfaceIdOption(interface_id=b'eth0'),
                                             ])

        with self.assertRaisesRegex(ValueError, r'not contain a message'):
            listening_socket.send_reply(outgoing_message)


if __name__ == '__main__':
    unittest.main()
