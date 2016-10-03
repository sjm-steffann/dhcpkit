"""
Test the RelayReplyMessage implementation
"""
import codecs
import unittest
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.duids import LinkLayerDUID, LinkLayerTimeDUID
from dhcpkit.ipv6.extensions.dns import RecursiveNameServersOption
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption
from dhcpkit.ipv6.messages import AdvertiseMessage, RelayReplyMessage
from dhcpkit.ipv6.options import ClientIdOption, IAAddressOption, IANAOption, InterfaceIdOption, \
    ReconfigureAcceptOption, RelayMessageOption, ServerIdOption
from dhcpkit.tests.ipv6.messages import test_relay_server_message

""

# DHCPv6
#     Message type: Relay-reply (13)
#     Hop count: 1
#     Link address: 2001:db8:ffff:1::1 (2001:db8:ffff:1::1)
#     Peer address: fe80::3631:c4ff:fe3c:b2f1 (fe80::3631:c4ff:fe3c:b2f1)
#     Interface-Id
#         Option: Interface-Id (18)
#         Length: 7
#         Value: 4769302f302f30
#         Interface-ID: 4769302f302f30
#     Relay Message
#         Option: Relay Message (9)
#         Length: 196
#         Value: 0d0000000000000000000000000000000000fe8000000000...
#         DHCPv6
#             Message type: Relay-reply (13)
#             Hop count: 0
#             Link address: :: (::)
#             Peer address: fe80::3631:c4ff:fe3c:b2f1 (fe80::3631:c4ff:fe3c:b2f1)
#             Interface-Id
#                 Option: Interface-Id (18)
#                 Length: 5
#                 Value: 4661322f33
#                 Interface-ID: 4661322f33
#             Relay Message
#                 Option: Relay Message (9)
#                 Length: 149
#                 Value: 02f350d600030028c43cb2f1000000000000000000050018...
#                 DHCPv6
#                     Message type: Advertise (2)
#                     Transaction ID: 0xf350d6
#                     Identity Association for Non-temporary Address
#                         Option: Identity Association for Non-temporary Address (3)
#                         Length: 40
#                         Value: c43cb2f100000000000000000005001820010db8ffff0001...
#                         IAID: c43cb2f1
#                         T1: 0
#                         T2: 0
#                         IA Address
#                             Option: IA Address (5)
#                             Length: 24
#                             Value: 20010db8ffff0001000c00000000e09c0000017700000258
#                             IPv6 address: 2001:db8:ffff:1:c::e09c (2001:db8:ffff:1:c::e09c)
#                             Preferred lifetime: 375
#                             Valid lifetime: 600
#                     Identity Association for Prefix Delegation
#                         Option: Identity Association for Prefix Delegation (25)
#                         Length: 41
#                         Value: c43cb2f10000000000000000001a00190000017700000258...
#                         IAID: c43cb2f1
#                         T1: 0
#                         T2: 0
#                         IA Prefix
#                             Option: IA Prefix (26)
#                             Length: 25
#                             Value: 00000177000002583820010db8ffccfe0000000000000000...
#                             Preferred lifetime: 375
#                             Valid lifetime: 600
#                             Prefix length: 56
#                             Prefix address: 2001:db8:ffcc:fe00:: (2001:db8:ffcc:fe00::)
#                     Client Identifier
#                         Option: Client Identifier (1)
#                         Length: 10
#                         Value: 000300013431c43cb2f1
#                         DUID: 000300013431c43cb2f1
#                         DUID Type: link-layer address (3)
#                         Hardware type: Ethernet (1)
#                         Link-layer address: 34:31:c4:3c:b2:f1
#                     Server Identifier
#                         Option: Server Identifier (2)
#                         Length: 14
#                         Value: 000100011d1d49cf00137265ca42
#                         DUID: 000100011d1d49cf00137265ca42
#                         DUID Type: link-layer address plus time (1)
#                         Hardware type: Ethernet (1)
#                         DUID Time: Jun 24, 2015 12:58:23.000000000 CEST
#                         Link-layer address: 00:13:72:65:ca:42
#                     Reconfigure Accept
#                         Option: Reconfigure Accept (20)
#                         Length: 0
#                     DNS recursive name server
#                         Option: DNS recursive name server (23)
#                         Length: 16
#                         Value: 20014860486000000000000000008888
#                          1 DNS server address: 2001:4860:4860::8888 (2001:4860:4860::8888)

relayed_advertise_message = RelayReplyMessage(
    hop_count=1,
    link_address=IPv6Address('2001:db8:ffff:1::1'),
    peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
    options=[
        InterfaceIdOption(interface_id=b'Gi0/0/0'),
        RelayMessageOption(relayed_message=RelayReplyMessage(
            hop_count=0,
            link_address=IPv6Address('::'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RelayMessageOption(relayed_message=AdvertiseMessage(
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        IANAOption(iaid=bytes.fromhex('c43cb2f1'), options=[
                            IAAddressOption(address=IPv6Address('2001:db8:ffff:1:c::e09c'), preferred_lifetime=375,
                                            valid_lifetime=600),
                        ]),
                        IAPDOption(iaid=bytes.fromhex('c43cb2f1'), options=[
                            IAPrefixOption(prefix=IPv6Network('2001:db8:ffcc:fe00::/56'), preferred_lifetime=375,
                                           valid_lifetime=600),
                        ]),
                        ClientIdOption(duid=LinkLayerDUID(hardware_type=1,
                                                          link_layer_address=bytes.fromhex('3431c43cb2f1'))),
                        ServerIdOption(duid=LinkLayerTimeDUID(hardware_type=1, time=488458703,
                                                              link_layer_address=bytes.fromhex('00137265ca42'))),
                        ReconfigureAcceptOption(),
                        RecursiveNameServersOption(dns_servers=[IPv6Address('2001:4860:4860::8888')]),
                    ],
                ))
            ],
        ))
    ],
)

relayed_advertise_packet = codecs.decode('0d0120010db8ffff0001000000000000'
                                         '0001fe800000000000003631c4fffe3c'
                                         'b2f1001200074769302f302f30000900'
                                         'c40d0000000000000000000000000000'
                                         '000000fe800000000000003631c4fffe'
                                         '3cb2f1001200054661322f3300090095'
                                         '02f350d600030028c43cb2f100000000'
                                         '000000000005001820010db8ffff0001'
                                         '000c00000000e09c0000017700000258'
                                         '00190029c43cb2f10000000000000000'
                                         '001a001900000177000002583820010d'
                                         'b8ffccfe000000000000000000000100'
                                         '0a000300013431c43cb2f10002000e00'
                                         '0100011d1d49cf00137265ca42001400'
                                         '00001700102001486048600000000000'
                                         '0000008888', 'hex')


class RelayedAdvertiseMessageTestCase(test_relay_server_message.RelayServerMessageTestCase):
    def setUp(self):
        self.packet_fixture = relayed_advertise_packet
        self.message_fixture = relayed_advertise_message
        self.parse_packet()


if __name__ == '__main__':
    unittest.main()
