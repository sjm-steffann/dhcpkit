"""
Test the LeasequeryMessage implementation
"""
import unittest
from ipaddress import IPv6Address

from dhcpkit.ipv6.duids import LinkLayerDUID
from dhcpkit.ipv6.extensions.leasequery import LQQueryOption, LeasequeryMessage, OPTION_LQ_RELAY_DATA, QUERY_BY_ADDRESS
from dhcpkit.ipv6.options import ClientIdOption, OptionRequestOption
from dhcpkit.tests.ipv6.messages import test_message


class LeasequeryMessageTestCase(test_message.MessageTestCase):
    def setUp(self):
        self.packet_fixture = bytes.fromhex(
            '0e'  # Message type Leasequery
            'e86f0c'  # Transaction ID

            '0001'  # Option type 1: OPTION_CLIENT_ID
            '000a'  # Option length: 10
            '0003'  # DUID type: DUID_LL
            '0001'  # Hardware type: Ethernet
            '001ee6f77d00'  # MAC Address

            '002c'  # Option type 44: OPTION_LQ_QUERY
            '0017'  # Option length: 23
            '01'  # Query type: QUERY_BY_ADDRESS
            'fe800000000000000000000000000001'  # Link address: fe80::1

            '0006'  # Option type: OPTION_ORO
            '0002'  # Option length: 2
            '002f'  # Requested option: OPTION_LQ_RELAY_DATA
        )
        self.message_fixture = LeasequeryMessage(
            transaction_id=bytes.fromhex('e86f0c'),
            options=[
                ClientIdOption(duid=LinkLayerDUID(hardware_type=1, link_layer_address=bytes.fromhex('001ee6f77d00'))),
                LQQueryOption(
                    query_type=QUERY_BY_ADDRESS,
                    link_address=IPv6Address('fe80::1'),
                    options=[
                        OptionRequestOption(requested_options=[OPTION_LQ_RELAY_DATA]),
                    ]
                ),
            ]
        )
        self.parse_packet()


if __name__ == '__main__':
    unittest.main()
