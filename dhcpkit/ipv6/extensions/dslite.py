"""
Implementation of DS-Lite AFTR Name option as specified in :rfc:`6334`.
"""

from struct import pack
from typing import Union

from dhcpkit.ipv6.messages import AdvertiseMessage, InformationRequestMessage, RebindMessage, RenewMessage, \
    ReplyMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import Option
from dhcpkit.utils import encode_domain, parse_domain_bytes

OPTION_AFTR_NAME = 64


class AFTRNameOption(Option):
    """
    :rfc:`6334#section-3`

    The AFTR-Name option consists of option-code and option-len fields
    (as all DHCPv6 options have), and a variable-length tunnel-endpoint-
    name field containing a fully qualified domain name that refers to
    the AFTR to which the client MAY connect.

    The AFTR-Name option SHOULD NOT appear in any DHCPv6 messages other
    than the following: Solicit, Advertise, Request, Renew, Rebind,
    Information-Request, and Reply.

    The format of the AFTR-Name option is shown in the following figure:

    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-------------------------------+-------------------------------+
      |    OPTION_AFTR_NAME: 64       |          option-len           |
      +-------------------------------+-------------------------------+
      |                                                               |
      |                  tunnel-endpoint-name (FQDN)                  |
      |                                                               |
      +---------------------------------------------------------------+

    OPTION_AFTR_NAME
        64

    option-len
        Length of the tunnel-endpoint-name field in octets.

    tunnel-endpoint-name
        A fully qualified domain name of the AFTR tunnel endpoint.

    :type fqdn: str
    """

    option_type = OPTION_AFTR_NAME

    def __init__(self, fqdn: str = ''):
        self.fqdn = fqdn
        """Domain name of the AFTR tunnel endpoint"""

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.fqdn, str):
            raise ValueError("Tunnel endpoint name must be a string")

        # Let the domain encoder check for errors
        fqdn = encode_domain(self.fqdn)

        if len(fqdn) < 4:
            raise ValueError("The FQDN of the tunnel endpoint is too short")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may contain more data after the
        structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length, min_length=4)
        header_offset = my_offset

        # Parse the domain label
        max_offset = option_len + header_offset  # The option_len field counts bytes *after* the header fields
        name_len, self.fqdn = parse_domain_bytes(buffer, offset=offset + my_offset, length=option_len)
        my_offset += name_len

        if my_offset != max_offset:
            raise ValueError('Option length does not match the length of the included fqdn')

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        fqdn_buffer = encode_domain(self.fqdn)

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(fqdn_buffer)))
        buffer.extend(fqdn_buffer)
        return buffer


# Update the messages where this option may appear
SolicitMessage.add_may_contain(AFTRNameOption, 0, 1)
AdvertiseMessage.add_may_contain(AFTRNameOption, 0, 1)
RequestMessage.add_may_contain(AFTRNameOption, 0, 1)
RenewMessage.add_may_contain(AFTRNameOption, 0, 1)
RebindMessage.add_may_contain(AFTRNameOption, 0, 1)
InformationRequestMessage.add_may_contain(AFTRNameOption, 0, 1)
ReplyMessage.add_may_contain(AFTRNameOption, 0, 1)
