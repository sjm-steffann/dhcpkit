"""
Test the RequestMessage implementation
"""
import codecs
import unittest
from ipaddress import IPv6Address, IPv6Network

from dhcpkit.ipv6.duids import LinkLayerDUID
from dhcpkit.ipv6.extensions.dns import OPTION_DNS_SERVERS
from dhcpkit.ipv6.extensions.ntp import OPTION_NTP_SERVER
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, IAPrefixOption, OPTION_IA_PD
from dhcpkit.ipv6.extensions.sntp import OPTION_SNTP_SERVERS
from dhcpkit.ipv6.extensions.sol_max_rt import OPTION_INF_MAX_RT, OPTION_SOL_MAX_RT
from dhcpkit.ipv6.messages import ConfirmMessage
from dhcpkit.ipv6.options import ClientIdOption, ElapsedTimeOption, IAAddressOption, IANAOption, OPTION_IA_NA, \
    OPTION_VENDOR_OPTS, OptionRequestOption, VendorClassOption
from dhcpkit.tests.ipv6.messages import test_client_server_message

""

confirm_message = ConfirmMessage(
    transaction_id=bytes.fromhex('f350d6'),
    options=[
        ElapsedTimeOption(elapsed_time=104),
        ClientIdOption(duid=LinkLayerDUID(hardware_type=1, link_layer_address=bytes.fromhex('3431c43cb2f1'))),
        IANAOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAAddressOption(address=IPv6Address('2001:db8:ffff:1:c::e09c'), preferred_lifetime=375, valid_lifetime=600),
        ]),
        IAPDOption(iaid=bytes.fromhex('c43cb2f1'), options=[
            IAPrefixOption(prefix=IPv6Network('2001:db8:ffcc:fe00::/56'), preferred_lifetime=375, valid_lifetime=600),
        ]),
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

confirm_packet = codecs.decode(
    '04'
    'f350d6'
    '000800020068'
    '0001000a000300013431c43cb2f1'
    '00030028c43cb2f100000000000000000005001820010db8ffff0001000c00000000e09c0000017700000258'
    '00190029c43cb2f10000000000000000001a001900000177000002583820010db8ffccfe000000000000000000'
    '0006001000170038001f00190003001100520053'
    '0010000400000368', 'hex'
)


class RequestMessageTestCase(test_client_server_message.ClientServerMessageTestCase):
    def setUp(self):
        self.packet_fixture = confirm_packet
        self.message_fixture = confirm_message
        self.parse_packet()


if __name__ == '__main__':
    unittest.main()
