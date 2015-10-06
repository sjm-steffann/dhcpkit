"""
Test the RequestMessage implementation
"""
import unittest
import codecs
from ipaddress import IPv6Network, IPv6Address

from dhcpkit.ipv6.duids import LinkLayerDUID, LinkLayerTimeDUID
from dhcpkit.ipv6.messages import RequestMessage
from dhcpkit.ipv6.options import ElapsedTimeOption, ClientIdOption, IANAOption, \
    ReconfigureAcceptOption, OptionRequestOption, OPTION_IA_NA, OPTION_VENDOR_OPTS, VendorClassOption, \
    IAAddressOption, ServerIdOption
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, OPTION_IA_PD
from dhcpkit.ipv6.extensions.dns import OPTION_DNS_SERVERS
from dhcpkit.ipv6.extensions.sntp import OPTION_SNTP_SERVERS
from dhcpkit.ipv6.extensions.ntp import OPTION_NTP_SERVER
from dhcpkit.ipv6.extensions.sol_max_rt import OPTION_SOL_MAX_RT, OPTION_INF_MAX_RT
from tests.ipv6.messages import test_client_server_message

""

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

request_message = RequestMessage(
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        ElapsedTimeOption(elapsed_time=104),
        ClientIdOption(duid=LinkLayerDUID(hardware_type=1, link_layer_address=bytes.fromhex('3431c43cb2f1'))),
        ServerIdOption(duid=LinkLayerTimeDUID(hardware_type=1, time=488458703,
                                              link_layer_address=bytes.fromhex('00137265ca42'))),
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


class RequestMessageTestCase(test_client_server_message.ClientServerMessageTestCase):
    def setUp(self):
        self.packet_fixture = request_packet
        self.message_fixture = request_message
        self.parse_packet()


if __name__ == '__main__':
    unittest.main()
