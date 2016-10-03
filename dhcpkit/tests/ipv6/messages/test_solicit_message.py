"""
Test the SolicitMessage implementation
"""
import codecs
import unittest
from ipaddress import IPv6Network

from dhcpkit.ipv6.duids import LinkLayerDUID
from dhcpkit.ipv6.extensions.dns import OPTION_DNS_SERVERS
from dhcpkit.ipv6.extensions.ntp import OPTION_NTP_SERVER
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, OPTION_IA_PD
from dhcpkit.ipv6.extensions.sntp import OPTION_SNTP_SERVERS
from dhcpkit.ipv6.extensions.sol_max_rt import OPTION_INF_MAX_RT, OPTION_SOL_MAX_RT
from dhcpkit.ipv6.messages import SolicitMessage
from dhcpkit.ipv6.options import ClientIdOption, ElapsedTimeOption, IANAOption, OPTION_IA_NA, OPTION_VENDOR_OPTS, \
    OptionRequestOption, RapidCommitOption, ReconfigureAcceptOption, VendorClassOption
from dhcpkit.tests.ipv6.messages import test_client_server_message

""

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

solicit_message = SolicitMessage(
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        ElapsedTimeOption(elapsed_time=0),
        ClientIdOption(duid=LinkLayerDUID(hardware_type=1, link_layer_address=bytes.fromhex('3431c43cb2f1'))),
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


class SolicitMessageTestCase(test_client_server_message.ClientServerMessageTestCase):
    def setUp(self):
        self.packet_fixture = solicit_packet
        self.message_fixture = solicit_message
        self.parse_packet()


if __name__ == '__main__':
    unittest.main()
