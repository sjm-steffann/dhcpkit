# http://www.iana.org/go/rfc5908
from struct import pack

from dhcp.ipv6 import option_registry
from dhcp.ipv6.options import Option
from dhcp.ipv6.rfc5908.suboptions import NTPSubOption

OPTION_NTP_SERVER = 56


class NTPServerOption(Option):
    """
    http://tools.ietf.org/html/rfc5908#section-4

    This option serves as a container for server location information
    related to one NTP server or Simple Network Time Protocol (SNTP)
    [RFC4330] server.  This option can appear multiple times in a DHCPv6
    message.  Each instance of this option is to be considered by the NTP
    client or SNTP client as a server to include in its configuration.

    The option itself does not contain any value.  Instead, it contains
    one or several suboptions that carry NTP server or SNTP server
    location.  This option MUST include one, and only one, time source
    suboption.  The currently defined time source suboptions are
    NTP_OPTION_SRV_ADDR, NTP_OPTION_SRV_MC_ADDR, and NTP_OPTION_SRV_FQDN.
    It carries the NTP server or SNTP server location as a unicast or
    multicast IPv6 address or as an NTP server or SNTP server FQDN.  More
    time source suboptions may be defined in the future.  While the FQDN
    option offers the most deployment flexibility, resiliency as well as
    security, the IP address options are defined to cover cases where a
    DNS dependency is not desirable.

    If the NTP server or SNTP server location is an IPv6 multicast
    address, the client SHOULD use this address as an NTP multicast group
    address and listen to messages sent to this group in order to
    synchronize its clock.

    The format of the NTP Server Option is:

      0                   1                   2                   3
      0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |      OPTION_NTP_SERVER        |          option-len           |
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |                         suboption-1                           |
     :                                                               :
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |                         suboption-2                           |
     :                                                               :
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     :                                                               :
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
     |                         suboption-n                           |
     :                                                               :
     +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

       option-code: OPTION_NTP_SERVER (56),

       option-len: Total length of the included suboptions.

    This document does not define any priority relationship between the
    client's embedded configuration (if any) and the NTP or SNTP servers
    discovered via this option.  In particular, the client is allowed to
    simultaneously use its own configured NTP servers or SNTP servers and
    the servers discovered via DHCP.
    """

    option_type = OPTION_NTP_SERVER

    def __init__(self, options: [NTPSubOption]=None):
        self.options = options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset, option_len = self.parse_option_header(buffer, offset, length)
        header_offset = my_offset

        # Parse the options
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        while max_offset > my_offset:
            used_buffer, option = NTPSubOption.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed suboptions')

        return my_offset

    def save(self) -> bytes:
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(options_buffer)))
        buffer.extend(options_buffer)
        return buffer


option_registry.register(OPTION_NTP_SERVER, NTPServerOption)
