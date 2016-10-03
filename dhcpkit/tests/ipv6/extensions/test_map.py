"""
Test the Prefix Delegation option implementation
"""

import unittest
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from struct import pack, unpack

from dhcpkit.ipv6.extensions.map import OPTION_S46_CONT_LW, OPTION_S46_CONT_MAPE, OPTION_S46_CONT_MAPT, S46BROption, \
    S46DMROption, S46LWContainerOption, S46MapEContainerOption, S46MapTContainerOption, S46PortParametersOption, \
    S46RuleOption, S46V4V6BindingOption
from dhcpkit.tests.ipv6.options import test_option

# S46PortParametersOption
s46_port_parameters_option_bytes = bytes.fromhex('005d'  # option_type: OPTION_S46_PORTPARAMS
                                                 '0004'  # option_length
                                                 '06'  # offset
                                                 '07'  # psid_len
                                                 'fe00')  # psid
s46_port_parameters_option_object = S46PortParametersOption(offset=6, psid_len=7, psid=127)

# S46RuleOption
s46_rule_option_bytes = (bytes.fromhex('0059'  # option_type: OPTION_S46_RULE
                                       '0015'  # option_length
                                       '01'  # flags
                                       '10'  # ea_len
                                       '18'  # ipv4_prefix_len
                                       '01020300'  # ipv4_prefix
                                       '22'  # ipv6_prefix_len
                                       '20010db800')  # ipv6_prefix
                         + s46_port_parameters_option_bytes)
s46_rule_option_object = S46RuleOption(flags=1, ea_len=16,
                                       ipv4_prefix=IPv4Network('1.2.3.0/24'),
                                       ipv6_prefix=IPv6Network('2001:db8::/34'),
                                       options=[s46_port_parameters_option_object])

# S46BROption
s46_br_option_bytes = bytes.fromhex('005a'  # option_type: OPTION_S46_BR
                                    '0010'  # option_length
                                    '20010db8000000000000000000000001')  # 2001:db8::1
s46_br_option_object = S46BROption(br_address=IPv6Address('2001:db8::1'))

# S46DMROption
s46_dmr_option_bytes = bytes.fromhex('005b'  # option_type: OPTION_S46_DMR
                                     '0006'  # option_length
                                     '21'  # prefix_len
                                     '20010db800')  # 2001:db8::1
s46_dmr_option_object = S46DMROption(dmr_prefix=IPv6Network('2001:db8::/33'))

# S46V4V6BindingOption
s46_v4_v6_binding_option_bytes = (bytes.fromhex('005c'  # option_type: OPTION_S46_V4V6BIND
                                                '0012'  # option_length
                                                '01020304'  # ipv4_address
                                                '22'  # ipv6_prefix_len
                                                '20010db800')  # ipv6_prefix
                                  + s46_port_parameters_option_bytes)

s46_v4_v6_binding_option_object = S46V4V6BindingOption(ipv4_address=IPv4Address('1.2.3.4'),
                                                       ipv6_prefix=IPv6Network('2001:db8::/34'),
                                                       options=[s46_port_parameters_option_object])


class S46RuleOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = s46_rule_option_bytes
        self.option_object = s46_rule_option_object
        self.parse_option()

    def test_flags(self):
        self.option.flags = 0
        self.assertFalse(self.option.fmr)
        self.assertEqual(self.option.flags, 0)

        self.option.fmr = True
        self.assertTrue(self.option.fmr)
        self.assertEqual(self.option.flags, 1)

        self.option.fmr = False
        self.assertFalse(self.option.fmr)
        self.assertEqual(self.option.flags, 0)

    def test_validate_flags(self):
        self.check_unsigned_integer_property('flags', 8)

    def test_validate_ea_len(self):
        with self.assertRaisesRegex(ValueError, 'range from 0 to 48'):
            self.option.ea_len = 0.1
            self.option.validate()

        self.option.ea_len = 0
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'range from 0 to 48'):
            self.option.ea_len = -1
            self.option.validate()

        self.option.ea_len = 48
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'range from 0 to 48'):
            self.option.ea_len = 49
            self.option.validate()

    def test_validate_ipv4_prefix(self):
        with self.assertRaisesRegex(ValueError, 'IPv4Network'):
            self.option.ipv4_prefix = None
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'IPv4Network'):
            self.option.ipv4_prefix = IPv4Address('1.2.3.4')
            self.option.validate()

        self.option.ipv4_prefix = IPv4Network('1.2.3.0/24')
        self.option.validate()

    def test_validate_ipv6_prefix(self):
        with self.assertRaisesRegex(ValueError, 'IPv6Network'):
            self.option.ipv6_prefix = None
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'IPv6Network'):
            self.option.ipv6_prefix = IPv6Address('2001:db8::1')
            self.option.validate()

        self.option.ipv6_prefix = IPv6Network('2001:db8::/32')
        self.option.validate()

    def test_bad_ipv4_prefix_length(self):
        S46RuleOption.parse(bytes.fromhex('00590015011020010203002220010db800ffff0000fffe0000'))

        with self.assertRaisesRegex(ValueError, 'range from 0 to 32'):
            S46RuleOption.parse(bytes.fromhex('00590015011021010203002220010db800ffff0000fffe0000'))

    def test_bad_ipv6_prefix_length(self):
        S46RuleOption.parse(bytes.fromhex('00590020011020010203008020010db8000000000000000000000000ffff0000fffe0000'))

        with self.assertRaisesRegex(ValueError, 'range from 0 to 128'):
            S46RuleOption.parse(
                bytes.fromhex('00590021011020010203008120010db800000000000000000000000000ffff0000fffe0000')
            )

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            S46RuleOption.parse(bytes.fromhex('00590000011018010203002220010db800ffff0000fffe0000'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            S46RuleOption.parse(bytes.fromhex('00590014011018010203002220010db800ffff0000fffe0000'))


class S46BROptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = s46_br_option_bytes
        self.option_object = s46_br_option_object

        self.parse_option()

    def test_validate_br_address(self):
        with self.assertRaisesRegex(ValueError, 'IPv6Address'):
            self.option.br_address = None
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'IPv6Address'):
            self.option.br_address = IPv6Network('2001:db8::1/128')
            self.option.validate()

        self.option.br_address = IPv6Address('2001:db8::1')
        self.option.validate()


class S46DMROptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = s46_dmr_option_bytes
        self.option_object = s46_dmr_option_object

        self.parse_option()

    def test_validate_dmr_prefix(self):
        with self.assertRaisesRegex(ValueError, 'IPv6Network'):
            self.option.dmr_prefix = None
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'IPv6Network'):
            self.option.dmr_prefix = IPv6Address('2001:db8::1')
            self.option.validate()

        self.option.dmr_prefix = IPv6Network('2001:db8::/32')
        self.option.validate()

    def test_bad_ipv6_prefix_length(self):
        S46DMROption.parse(bytes.fromhex('005b00118020010db8000000000000000000000001'))

        with self.assertRaisesRegex(ValueError, 'range from 0 to 128'):
            S46DMROption.parse(
                bytes.fromhex('005b00118120010db800000000000000000000000100')
            )

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            S46DMROption.parse(
                bytes.fromhex('005b00112020010db8000000000000000000000000')
            )


class S46V4V6BindingOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = s46_v4_v6_binding_option_bytes
        self.option_object = s46_v4_v6_binding_option_object
        self.parse_option()

    def test_validate_ipv4_address(self):
        with self.assertRaisesRegex(ValueError, 'IPv4Address'):
            self.option.ipv4_address = None
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'IPv4Address'):
            self.option.ipv4_address = IPv4Network('1.2.3.0/24')
            self.option.validate()

        self.option.ipv4_address = IPv4Address('1.2.3.0')
        self.option.validate()

    def test_validate_ipv6_prefix(self):
        with self.assertRaisesRegex(ValueError, 'IPv6Network'):
            self.option.ipv6_prefix = None
            self.option.validate()

        with self.assertRaisesRegex(ValueError, 'IPv6Network'):
            self.option.ipv6_prefix = IPv6Address('2001:db8::1')
            self.option.validate()

        self.option.ipv6_prefix = IPv6Network('2001:db8::/32')
        self.option.validate()

    def test_bad_ipv6_prefix_length(self):
        S46V4V6BindingOption.parse(bytes.fromhex('005c001d010203048020010db8000000000000000000000000ffff0000fffe0000'))

        with self.assertRaisesRegex(ValueError, 'range from 0 to 128'):
            S46V4V6BindingOption.parse(
                bytes.fromhex('005c001f010203048120010db80000000000000000000000000000ffff0000fffe0000')
            )

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'shorter than the minimum length'):
            S46V4V6BindingOption.parse(bytes.fromhex('005c0001010203042020010db8ffff0000fffe0000'))

        with self.assertRaisesRegex(ValueError, 'length does not match'):
            S46V4V6BindingOption.parse(bytes.fromhex('005c0010010203042020010db8ffff0000fffe0000'))


class S46PortParametersOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = s46_port_parameters_option_bytes
        self.option_object = s46_port_parameters_option_object
        self.parse_option()

    def test_validate_offset(self):
        # Don't forget to set PSID-length to 0 to allow the full range of offsets
        self.option.psid_len = 0
        self.option.psid = 0

        self.check_unsigned_integer_property('offset', 4)

    def test_validate_psid_len(self):
        # Don't forget to set offset to 0 to allow the full range of PSID-length
        self.option.offset = 0
        self.option.psid = 0

        with self.assertRaisesRegex(ValueError, 'integer'):
            self.option.psid_len = 0.1
            self.option.validate()

        self.option.psid_len = 0
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'range from 0 to 16'):
            self.option.psid_len = -1
            self.option.validate()

        self.option.psid_len = 16
        self.option.validate()

        with self.assertRaisesRegex(ValueError, 'range from 0 to 16'):
            self.option.psid_len = 17
            self.option.validate()

    def test_validate_combined_offset_psid_len(self):
        # Don't forget to set PSID to 0, it's the only value that is always valid
        self.option.psid = 0

        # These should all be ok
        for offset in range(16):
            self.option.offset = offset
            self.option.psid_len = 16 - offset
            self.option.validate()

        # These should not
        for offset in range(1, 16):
            with self.assertRaisesRegex(ValueError, 'together must be 16 or less'):
                self.option.offset = offset
                self.option.psid_len = 17 - offset
                self.option.validate()

    def test_validate_psid(self):
        # Don't forget to set offset to 0 to allow the full range of PSID-length
        self.option.offset = 0

        for psid_len in range(17):
            self.option.psid_len = psid_len
            self.check_unsigned_integer_property('psid', psid_len)


class S46MapEContainerOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('005e{:04x}'.format(len(s46_rule_option_bytes) +
                                                              len(s46_br_option_bytes))) + \
                            s46_rule_option_bytes + \
                            s46_br_option_bytes

        self.option_object = S46MapEContainerOption(options=[
            s46_rule_option_object,
            s46_br_option_object,
        ])
        self.parse_option()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            # Use the "good" option and mess up the option length field intentionally
            old_len = unpack('!H', self.option_bytes[2:4])[0]
            option_bytes = pack('!HH', OPTION_S46_CONT_MAPE, old_len - 1) + self.option_bytes[4:]

            S46MapEContainerOption.parse(option_bytes)


class S46MapTContainerOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('005f{:04x}'.format(len(s46_rule_option_bytes) +
                                                              len(s46_dmr_option_bytes))) + \
                            s46_rule_option_bytes + \
                            s46_dmr_option_bytes

        self.option_object = S46MapTContainerOption(options=[
            s46_rule_option_object,
            s46_dmr_option_object,
        ])
        self.parse_option()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            # Use the "good" option and mess up the option length field intentionally
            old_len = unpack('!H', self.option_bytes[2:4])[0]
            option_bytes = pack('!HH', OPTION_S46_CONT_MAPT, old_len - 1) + self.option_bytes[4:]

            S46MapTContainerOption.parse(option_bytes)


class S46LWContainerOptionTestCase(test_option.OptionTestCase):
    def setUp(self):
        self.option_bytes = bytes.fromhex('0060{:04x}'.format(len(s46_v4_v6_binding_option_bytes) +
                                                              len(s46_br_option_bytes))) + \
                            s46_v4_v6_binding_option_bytes + \
                            s46_br_option_bytes

        self.option_object = S46LWContainerOption(options=[
            s46_v4_v6_binding_option_object,
            s46_br_option_object,
        ])
        self.parse_option()

    def test_bad_option_length(self):
        with self.assertRaisesRegex(ValueError, 'length does not match'):
            # Use the "good" option and mess up the option length field intentionally
            old_len = unpack('!H', self.option_bytes[2:4])[0]
            option_bytes = pack('!HH', OPTION_S46_CONT_LW, old_len - 1) + self.option_bytes[4:]

            S46LWContainerOption.parse(option_bytes)


if __name__ == '__main__':
    unittest.main()
