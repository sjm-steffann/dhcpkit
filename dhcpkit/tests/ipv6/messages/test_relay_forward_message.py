"""
Test the RelayForwardMessage implementation
"""
import codecs
import unittest
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.duids import LinkLayerDUID
from dhcpkit.ipv6.extensions.dns import OPTION_DNS_SERVERS
from dhcpkit.ipv6.extensions.ntp import OPTION_NTP_SERVER
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, OPTION_IA_PD
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.extensions.sntp import OPTION_SNTP_SERVERS
from dhcpkit.ipv6.extensions.sol_max_rt import OPTION_INF_MAX_RT, OPTION_SOL_MAX_RT
from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage, ReplyMessage, SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, ElapsedTimeOption, IANAOption, InterfaceIdOption, OPTION_IA_NA, \
    OPTION_VENDOR_OPTS, OptionRequestOption, RapidCommitOption, ReconfigureAcceptOption, RelayMessageOption, \
    VendorClassOption
from dhcpkit.tests.ipv6.messages import test_relay_server_message
from dhcpkit.tests.ipv6.messages.test_reply_message import reply_message

""

# DHCPv6
#     Message type: Relay-forw (12)
#     Hop count: 1
#     Link address: 2001:db8:ffff:1::1 (2001:db8:ffff:1::1)
#     Peer address: fe80::3631:c4ff:fe3c:b2f1 (fe80::3631:c4ff:fe3c:b2f1)
#     Relay Message
#         Option: Relay Message (9)
#         Length: 194
#         Value: 0c0000000000000000000000000000000000fe8000000000...
#         DHCPv6
#             Message type: Relay-forw (12)
#             Hop count: 0
#             Link address: :: (::)
#             Peer address: fe80::3631:c4ff:fe3c:b2f1 (fe80::3631:c4ff:fe3c:b2f1)
#             Relay Message
#                 Option: Relay Message (9)
#                 Length: 121
#                 Value: 01f350d60008000200000001000a000300013431c43cb2f1...
#                 DHCPv6
#                     Message type: Solicit (1)
#                     Transaction ID: 0xf350d6
#                     Elapsed time
#                         Option: Elapsed time (8)
#                         Length: 2
#                         Value: 0000
#                         Elapsed time: 0 ms
#                     Client Identifier
#                         Option: Client Identifier (1)
#                         Length: 10
#                         Value: 000300013431c43cb2f1
#                         DUID: 000300013431c43cb2f1
#                         DUID Type: link-layer address (3)
#                         Hardware type: Ethernet (1)
#                         Link-layer address: 34:31:c4:3c:b2:f1
#                     Rapid Commit
#                         Option: Rapid Commit (14)
#                         Length: 0
#                     Identity Association for Non-temporary Address
#                         Option: Identity Association for Non-temporary Address (3)
#                         Length: 12
#                         Value: c43cb2f10000000000000000
#                         IAID: c43cb2f1
#                         T1: 0
#                         T2: 0
#                     Identity Association for Prefix Delegation
#                         Option: Identity Association for Prefix Delegation (25)
#                         Length: 41
#                         Value: c43cb2f10000000000000000001a00190000000000000000...
#                         IAID: c43cb2f1
#                         T1: 0
#                         T2: 0
#                         IA Prefix
#                             Option: IA Prefix (26)
#                             Length: 25
#                             Value: 000000000000000000000000000000000000000000000000...
#                             Preferred lifetime: 0
#                             Valid lifetime: 0
#                             Prefix length: 0
#                             Prefix address: :: (::)
#                     Reconfigure Accept
#                         Option: Reconfigure Accept (20)
#                         Length: 0
#                     Option Request
#                         Option: Option Request (6)
#                         Length: 16
#                         Value: 00170038001f00190003001100520053
#                         Requested Option code: DNS recursive name server (23)
#                         Requested Option code: NTP Server (56)
#                         Requested Option code: Simple Network Time Protocol Server (31)
#                         Requested Option code: Identity Association for Prefix Delegation (25)
#                         Requested Option code: Identity Association for Non-temporary Address (3)
#                         Requested Option code: Vendor-specific Information (17)
#                         Requested Option code: SOL_MAX_RT (82)
#                         Requested Option code: INF_MAX_RT (83)
#                     Vendor Class
#                         Option: Vendor Class (16)
#                         Length: 4
#                         Value: 00000368
#                         Enterprise ID: AVM GmbH (872)
#             Interface-Id
#                 Option: Interface-Id (18)
#                 Length: 5
#                 Value: 4661322f33
#                 Interface-ID: 4661322f33
#             Remote Identifier
#                 Option: Remote Identifier (37)
#                 Length: 22
#                 Value: 00000009020023000001000a0003000100211c7d486e
#                 Enterprise ID: ciscoSystems (9)
#                 Remote-ID: 020023000001000a0003000100211c7d486e
#     Interface-Id
#         Option: Interface-Id (18)
#         Length: 7
#         Value: 4769302f302f30
#         Interface-ID: 4769302f302f30
#     Remote Identifier
#         Option: Remote Identifier (37)
#         Length: 22
#         Value: 00000009020000000000000a0003000124e9b36e8100
#         Enterprise ID: ciscoSystems (9)
#         Remote-ID: 020000000000000a0003000124e9b36e8100

relayed_solicit_message = RelayForwardMessage(
    hop_count=1,
    link_address=IPv6Address('2001:db8:ffff:1::1'),
    peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
    options=[
        RelayMessageOption(relayed_message=RelayForwardMessage(
            hop_count=0,
            link_address=IPv6Address('::'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=SolicitMessage(
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        ElapsedTimeOption(elapsed_time=0),
                        ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                          link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                        RapidCommitOption(),
                        IANAOption(iaid=bytes.fromhex('c43cb2f1')),
                        IAPDOption(iaid=bytes.fromhex('c43cb2f1'), options=[
                            IAPrefixOption(prefix=IPv6Network('::/0')),
                        ]),
                        ReconfigureAcceptOption(),
                        OptionRequestOption(requested_options=[
                            OPTION_DNS_SERVERS,
                            OPTION_NTP_SERVER,
                            OPTION_SNTP_SERVERS,
                            OPTION_IA_PD,
                            OPTION_IA_NA,
                            OPTION_VENDOR_OPTS,
                            OPTION_SOL_MAX_RT,
                            OPTION_INF_MAX_RT,
                        ]),
                        VendorClassOption(enterprise_number=872),
                    ],
                )),
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RemoteIdOption(enterprise_number=9, remote_id=bytes.fromhex('020023000001000a0003000100211c7d486e')),
            ])
        ),
        InterfaceIdOption(interface_id=b'Gi0/0/0'),
        RemoteIdOption(enterprise_number=9, remote_id=bytes.fromhex('020000000000000a0003000124e9b36e8100')),
    ],
)

relayed_solicit_packet = codecs.decode('0c0120010db8ffff0001000000000000'
                                       '0001fe800000000000003631c4fffe3c'
                                       'b2f1000900c20c000000000000000000'
                                       '0000000000000000fe80000000000000'
                                       '3631c4fffe3cb2f10009007901f350d6'
                                       '0008000200000001000a000300013431'
                                       'c43cb2f1000e00000003000cc43cb2f1'
                                       '000000000000000000190029c43cb2f1'
                                       '0000000000000000001a001900000000'
                                       '00000000000000000000000000000000'
                                       '00000000000014000000060010001700'
                                       '38001f00190003001100520053001000'
                                       '0400000368001200054661322f330025'
                                       '001600000009020023000001000a0003'
                                       '000100211c7d486e001200074769302f'
                                       '302f3000250016000000090200000000'
                                       '00000a0003000124e9b36e8100', 'hex')


class RelayedSolicitMessageTestCase(test_relay_server_message.RelayServerMessageTestCase):
    def setUp(self):
        self.packet_fixture = relayed_solicit_packet
        self.message_fixture = relayed_solicit_message
        self.parse_packet()

    def test_wrap_response(self):
        response = self.message.wrap_response(reply_message)
        self.assertIsInstance(response, RelayReplyMessage)
        self.assertEqual(response.hop_count, 1)
        self.assertEqual(response.link_address, IPv6Address('2001:db8:ffff:1::1'))
        self.assertEqual(response.peer_address, IPv6Address('fe80::3631:c4ff:fe3c:b2f1'))

        one_level_in = response.relayed_message
        self.assertIsInstance(one_level_in, RelayReplyMessage)
        self.assertEqual(one_level_in.hop_count, 0)
        self.assertEqual(one_level_in.link_address, IPv6Address('::'))
        self.assertEqual(one_level_in.peer_address, IPv6Address('fe80::3631:c4ff:fe3c:b2f1'))

        two_levels_in = one_level_in.relayed_message
        self.assertIsInstance(two_levels_in, ReplyMessage)
        self.assertEqual(two_levels_in.transaction_id, b'\xf3P\xd6')


if __name__ == '__main__':
    unittest.main()
