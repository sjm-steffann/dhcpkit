import codecs
from ipaddress import IPv6Network, IPv6Address

from dhcp.ipv6.messages import ClientServerMessage, MSG_SOLICIT, MSG_ADVERTISE, MSG_REQUEST, MSG_REPLY, \
    RelayServerMessage, MSG_RELAY_FORW, MSG_RELAY_REPL
from dhcp.ipv6.options import ElapsedTimeOption, ClientIdOption, RapidCommitOption, IANAOption, \
    ReconfigureAcceptOption, OptionRequestOption, OPTION_IA_NA, OPTION_VENDOR_OPTS, VendorClassOption, \
    IAAddressOption, ServerIdOption, RelayMessageOption, InterfaceIdOption
from dhcp.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, OPTION_IA_PD
from dhcp.ipv6.extensions.dns import OPTION_DNS_SERVERS, DNSRecursiveNameServersOption
from dhcp.ipv6.extensions.sntp import OPTION_SNTP_SERVERS
from dhcp.ipv6.extensions.remote_id import RemoteIdOption
from dhcp.ipv6.extensions.ntp import OPTION_NTP_SERVER
from dhcp.ipv6.extensions.sol_max_rt import OPTION_SOL_MAX_RT, OPTION_INF_MAX_RT



# DHCPv6
#   Message type: Solicit (1)
#   Transaction ID: 0xf350d6
#   Elapsed time
#     Option: Elapsed time (8)
#     Length: 2
#     Value: 0000
#     Elapsed time: 0 ms
#   Client Identifier
#     Option: Client Identifier (1)
#     Length: 10
#     Value: 000300013431c43cb2f1
#     DUID: 000300013431c43cb2f1
#     DUID Type: link-layer address (3)
#     Hardware type: Ethernet (1)
#     Link-layer address: 34:31:c4:3c:b2:f1
#   Rapid Commit
#     Option: Rapid Commit (14)
#     Length: 0
#   Identity Association for Non-temporary Address
#     Option: Identity Association for Non-temporary Address (3)
#     Length: 12
#     Value: c43cb2f10000000000000000
#     IAID: c43cb2f1
#     T1: 0
#     T2: 0
#   Identity Association for Prefix Delegation
#     Option: Identity Association for Prefix Delegation (25)
#     Length: 41
#     Value: c43cb2f10000000000000000001a00190000000000000000...
#     IAID: c43cb2f1
#     T1: 0
#     T2: 0
#     IA Prefix
#       Option: IA Prefix (26)
#       Length: 25
#       Value: 000000000000000000000000000000000000000000000000...
#       Preferred lifetime: 0
#       Valid lifetime: 0
#       Prefix length: 0
#       Prefix address: :: (::)
#   Reconfigure Accept
#     Option: Reconfigure Accept (20)
#     Length: 0
#   Option Request
#     Option: Option Request (6)
#     Length: 16
#     Value: 00170038001f00190003001100520053
#     Requested Option code: DNS recursive name server (23)
#     Requested Option code: NTP Server (56)
#     Requested Option code: Simple Network Time Protocol Server (31)
#     Requested Option code: Identity Association for Prefix Delegation (25)
#     Requested Option code: Identity Association for Non-temporary Address (3)
#     Requested Option code: Vendor-specific Information (17)
#     Requested Option code: SOL_MAX_RT (82)
#     Requested Option code: INF_MAX_RT (83)
#   Vendor Class
#     Option: Vendor Class (16)
#     Length: 4
#     Value: 00000368
#     Enterprise ID: AVM GmbH (872)

solicit_message = ClientServerMessage(
    message_type=MSG_SOLICIT,
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        ElapsedTimeOption(elapsed_time=0),
        ClientIdOption(duid=bytes.fromhex('000300013431c43cb2f1')),
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
)

solicit_packet = codecs.decode('01f350d60008000200000001000a0003'
                               '00013431c43cb2f1000e00000003000c'
                               'c43cb2f1000000000000000000190029'
                               'c43cb2f10000000000000000001a0019'
                               '00000000000000000000000000000000'
                               '00000000000000000000140000000600'
                               '1000170038001f001900030011005200'
                               '530010000400000368', 'hex')

# DHCPv6
#     Message type: Advertise (2)
#     Transaction ID: 0xf350d6
#     Identity Association for Non-temporary Address
#         Option: Identity Association for Non-temporary Address (3)
#         Length: 40
#         Value: c43cb2f100000000000000000005001820010db8ffff0001...
#         IAID: c43cb2f1
#         T1: 0
#         T2: 0
#         IA Address
#             Option: IA Address (5)
#             Length: 24
#             Value: 20010db8ffff0001000c00000000e09c0000017700000258
#             IPv6 address: 2001:db8:ffff:1:c::e09c (2001:db8:ffff:1:c::e09c)
#             Preferred lifetime: 375
#             Valid lifetime: 600
#     Identity Association for Prefix Delegation
#         Option: Identity Association for Prefix Delegation (25)
#         Length: 41
#         Value: c43cb2f10000000000000000001a00190000017700000258...
#         IAID: c43cb2f1
#         T1: 0
#         T2: 0
#         IA Prefix
#             Option: IA Prefix (26)
#             Length: 25
#             Value: 00000177000002583820010db8ffccfe0000000000000000...
#             Preferred lifetime: 375
#             Valid lifetime: 600
#             Prefix length: 56
#             Prefix address: 2001:db8:ffcc:fe00:: (2001:db8:ffcc:fe00::)
#     Client Identifier
#         Option: Client Identifier (1)
#         Length: 10
#         Value: 000300013431c43cb2f1
#         DUID: 000300013431c43cb2f1
#         DUID Type: link-layer address (3)
#         Hardware type: Ethernet (1)
#         Link-layer address: 34:31:c4:3c:b2:f1
#     Server Identifier
#         Option: Server Identifier (2)
#         Length: 14
#         Value: 000100011d1d49cf00137265ca42
#         DUID: 000100011d1d49cf00137265ca42
#         DUID Type: link-layer address plus time (1)
#         Hardware type: Ethernet (1)
#         DUID Time: Jun 24, 2015 12:58:23.000000000 CEST
#         Link-layer address: 00:13:72:65:ca:42
#     Reconfigure Accept
#         Option: Reconfigure Accept (20)
#         Length: 0
#     DNS recursive name server
#         Option: DNS recursive name server (23)
#         Length: 16
#         Value: 20014860486000000000000000008888
#          1 DNS server address: 2001:4860:4860::8888 (2001:4860:4860::8888)

advertise_message = ClientServerMessage(
    message_type=MSG_ADVERTISE,
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        IANAOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAAddressOption(address=IPv6Address('2001:db8:ffff:1:c::e09c'), preferred_lifetime=375, valid_lifetime=600),
        ]),
        IAPDOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAPrefixOption(prefix=IPv6Network('2001:db8:ffcc:fe00::/56'), preferred_lifetime=375, valid_lifetime=600),
        ]),
        ClientIdOption(duid=bytes.fromhex('000300013431c43cb2f1')),
        ServerIdOption(duid=bytes.fromhex('000100011d1d49cf00137265ca42')),
        ReconfigureAcceptOption(),
        DNSRecursiveNameServersOption(dns_servers=[IPv6Address('2001:4860:4860::8888')]),
    ],
)

advertise_packet = codecs.decode('02f350d600030028c43cb2f100000000'
                                 '000000000005001820010db8ffff0001'
                                 '000c00000000e09c0000017700000258'
                                 '00190029c43cb2f10000000000000000'
                                 '001a001900000177000002583820010d'
                                 'b8ffccfe000000000000000000000100'
                                 '0a000300013431c43cb2f10002000e00'
                                 '0100011d1d49cf00137265ca42001400'
                                 '00001700102001486048600000000000'
                                 '0000008888', 'hex')

# DHCPv6
#     Message type: Request (3)
#     Transaction ID: 0xf350d6
#     Elapsed time
#         Option: Elapsed time (8)
#         Length: 2
#         Value: 0068
#         Elapsed time: 104 ms
#     Client Identifier
#         Option: Client Identifier (1)
#         Length: 10
#         Value: 000300013431c43cb2f1
#         DUID: 000300013431c43cb2f1
#         DUID Type: link-layer address (3)
#         Hardware type: Ethernet (1)
#         Link-layer address: 34:31:c4:3c:b2:f1
#     Server Identifier
#         Option: Server Identifier (2)
#         Length: 14
#         Value: 000100011d1d49cf00137265ca42
#         DUID: 000100011d1d49cf00137265ca42
#         DUID Type: link-layer address plus time (1)
#         Hardware type: Ethernet (1)
#         DUID Time: Jun 24, 2015 12:58:23.000000000 CEST
#         Link-layer address: 00:13:72:65:ca:42
#     Identity Association for Non-temporary Address
#         Option: Identity Association for Non-temporary Address (3)
#         Length: 40
#         Value: c43cb2f100000000000000000005001820010db8ffff0001...
#         IAID: c43cb2f1
#         T1: 0
#         T2: 0
#         IA Address
#             Option: IA Address (5)
#             Length: 24
#             Value: 20010db8ffff0001000c00000000e09c0000017700000258
#             IPv6 address: 2001:db8:ffff:1:c::e09c (2001:db8:ffff:1:c::e09c)
#             Preferred lifetime: 375
#             Valid lifetime: 600
#     Identity Association for Prefix Delegation
#         Option: Identity Association for Prefix Delegation (25)
#         Length: 41
#         Value: c43cb2f10000000000000000001a00190000017700000258...
#         IAID: c43cb2f1
#         T1: 0
#         T2: 0
#         IA Prefix
#             Option: IA Prefix (26)
#             Length: 25
#             Value: 00000177000002583820010db8ffccfe0000000000000000...
#             Preferred lifetime: 375
#             Valid lifetime: 600
#             Prefix length: 56
#             Prefix address: 2001:db8:ffcc:fe00:: (2001:db8:ffcc:fe00::)
#     Reconfigure Accept
#         Option: Reconfigure Accept (20)
#         Length: 0
#     Option Request
#         Option: Option Request (6)
#         Length: 16
#         Value: 00170038001f00190003001100520053
#         Requested Option code: DNS recursive name server (23)
#         Requested Option code: NTP Server (56)
#         Requested Option code: Simple Network Time Protocol Server (31)
#         Requested Option code: Identity Association for Prefix Delegation (25)
#         Requested Option code: Identity Association for Non-temporary Address (3)
#         Requested Option code: Vendor-specific Information (17)
#         Requested Option code: SOL_MAX_RT (82)
#         Requested Option code: INF_MAX_RT (83)
#     Vendor Class
#         Option: Vendor Class (16)
#         Length: 4
#         Value: 00000368
#         Enterprise ID: AVM GmbH (872)

request_message = ClientServerMessage(
    message_type=MSG_REQUEST,
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        ElapsedTimeOption(elapsed_time=104),
        ClientIdOption(duid=bytes.fromhex('000300013431c43cb2f1')),
        ServerIdOption(duid=bytes.fromhex('000100011d1d49cf00137265ca42')),
        IANAOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAAddressOption(address=IPv6Address('2001:db8:ffff:1:c::e09c'), preferred_lifetime=375, valid_lifetime=600),
        ]),
        IAPDOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAPrefixOption(prefix=IPv6Network('2001:db8:ffcc:fe00::/56'), preferred_lifetime=375, valid_lifetime=600),
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
)

request_packet = codecs.decode('03f350d60008000200680001000a0003'
                               '00013431c43cb2f10002000e00010001'
                               '1d1d49cf00137265ca4200030028c43c'
                               'b2f10000000000000000000500182001'
                               '0db8ffff0001000c00000000e09c0000'
                               '01770000025800190029c43cb2f10000'
                               '000000000000001a0019000001770000'
                               '02583820010db8ffccfe000000000000'
                               '00000000140000000600100017003800'
                               '1f001900030011005200530010000400'
                               '000368', 'hex')

# DHCPv6
#     Message type: Reply (7)
#     Transaction ID: 0xf350d6
#     Identity Association for Non-temporary Address
#         Option: Identity Association for Non-temporary Address (3)
#         Length: 40
#         Value: c43cb2f100000000000000000005001820010db8ffff0001...
#         IAID: c43cb2f1
#         T1: 0
#         T2: 0
#         IA Address
#             Option: IA Address (5)
#             Length: 24
#             Value: 20010db8ffff0001000c00000000e09c0000017700000258
#             IPv6 address: 2001:db8:ffff:1:c::e09c (2001:db8:ffff:1:c::e09c)
#             Preferred lifetime: 375
#             Valid lifetime: 600
#     Identity Association for Prefix Delegation
#         Option: Identity Association for Prefix Delegation (25)
#         Length: 41
#         Value: c43cb2f10000000000000000001a00190000017700000258...
#         IAID: c43cb2f1
#         T1: 0
#         T2: 0
#         IA Prefix
#             Option: IA Prefix (26)
#             Length: 25
#             Value: 00000177000002583820010db8ffccfe0000000000000000...
#             Preferred lifetime: 375
#             Valid lifetime: 600
#             Prefix length: 56
#             Prefix address: 2001:db8:ffcc:fe00:: (2001:db8:ffcc:fe00::)
#     Client Identifier
#         Option: Client Identifier (1)
#         Length: 10
#         Value: 000300013431c43cb2f1
#         DUID: 000300013431c43cb2f1
#         DUID Type: link-layer address (3)
#         Hardware type: Ethernet (1)
#         Link-layer address: 34:31:c4:3c:b2:f1
#     Server Identifier
#         Option: Server Identifier (2)
#         Length: 14
#         Value: 000100011d1d49cf00137265ca42
#         DUID: 000100011d1d49cf00137265ca42
#         DUID Type: link-layer address plus time (1)
#         Hardware type: Ethernet (1)
#         DUID Time: Jun 24, 2015 12:58:23.000000000 CEST
#         Link-layer address: 00:13:72:65:ca:42
#     Reconfigure Accept
#         Option: Reconfigure Accept (20)
#         Length: 0
#     DNS recursive name server
#         Option: DNS recursive name server (23)
#         Length: 16
#         Value: 20014860486000000000000000008888
#          1 DNS server address: 2001:4860:4860::8888 (2001:4860:4860::8888)

reply_message = ClientServerMessage(
    message_type=MSG_REPLY,
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        IANAOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAAddressOption(address=IPv6Address('2001:db8:ffff:1:c::e09c'), preferred_lifetime=375, valid_lifetime=600),
        ]),
        IAPDOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAPrefixOption(prefix=IPv6Network('2001:db8:ffcc:fe00::/56'), preferred_lifetime=375, valid_lifetime=600),
        ]),
        ClientIdOption(duid=bytes.fromhex('000300013431c43cb2f1')),
        ServerIdOption(duid=bytes.fromhex('000100011d1d49cf00137265ca42')),
        ReconfigureAcceptOption(),
        DNSRecursiveNameServersOption(dns_servers=[IPv6Address('2001:4860:4860::8888')]),
    ],
)

reply_packet = codecs.decode('07f350d600030028c43cb2f100000000'
                             '000000000005001820010db8ffff0001'
                             '000c00000000e09c0000017700000258'
                             '00190029c43cb2f10000000000000000'
                             '001a001900000177000002583820010d'
                             'b8ffccfe000000000000000000000100'
                             '0a000300013431c43cb2f10002000e00'
                             '0100011d1d49cf00137265ca42001400'
                             '00001700102001486048600000000000'
                             '0000008888', 'hex')

# DHCPv6
#     Message type: Relay-forw (12)
#     Hopcount: 1
#     Link address: 2001:db8:ffff:1::1 (2001:db8:ffff:1::1)
#     Peer address: fe80::3631:c4ff:fe3c:b2f1 (fe80::3631:c4ff:fe3c:b2f1)
#     Relay Message
#         Option: Relay Message (9)
#         Length: 194
#         Value: 0c0000000000000000000000000000000000fe8000000000...
#         DHCPv6
#             Message type: Relay-forw (12)
#             Hopcount: 0
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

relayed_solicit_message = RelayServerMessage(
    message_type=MSG_RELAY_FORW,
    hop_count=1,
    link_address=IPv6Address('2001:db8:ffff:1::1'),
    peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
    options=[
        RelayMessageOption(relayed_message=RelayServerMessage(
            message_type=MSG_RELAY_FORW,
            hop_count=0,
            link_address=IPv6Address('::'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                RelayMessageOption(relayed_message=ClientServerMessage(
                    message_type=MSG_SOLICIT,
                    transaction_id=bytes.fromhex('f350d6'),
                    options=[
                        ElapsedTimeOption(elapsed_time=0),
                        ClientIdOption(duid=bytes.fromhex('000300013431c43cb2f1')),
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

# DHCPv6
#     Message type: Relay-reply (13)
#     Hopcount: 1
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
#             Hopcount: 0
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

relayed_advertise_message = RelayServerMessage(
    message_type=MSG_RELAY_REPL,
    hop_count=1,
    link_address=IPv6Address('2001:db8:ffff:1::1'),
    peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
    options=[
        InterfaceIdOption(interface_id=b'Gi0/0/0'),
        RelayMessageOption(relayed_message=RelayServerMessage(
            message_type=MSG_RELAY_REPL,
            hop_count=0,
            link_address=IPv6Address('::'),
            peer_address=IPv6Address('fe80::3631:c4ff:fe3c:b2f1'),
            options=[
                InterfaceIdOption(interface_id=b'Fa2/3'),
                RelayMessageOption(relayed_message=ClientServerMessage(
                    message_type=MSG_ADVERTISE,
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
                        ClientIdOption(duid=bytes.fromhex('000300013431c43cb2f1')),
                        ServerIdOption(duid=bytes.fromhex('000100011d1d49cf00137265ca42')),
                        ReconfigureAcceptOption(),
                        DNSRecursiveNameServersOption(dns_servers=[IPv6Address('2001:4860:4860::8888')]),
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
