"""
Implementation of timezone options as specified in :rfc:`4833`.
"""
import re
import string
from struct import pack
from typing import Union

from dhcpkit.ipv6.messages import AdvertiseMessage, InformationRequestMessage, RebindMessage, RenewMessage, \
    ReplyMessage, RequestMessage, SolicitMessage
from dhcpkit.ipv6.options import Option

OPTION_NEW_POSIX_TIMEZONE = 41
OPTION_NEW_TZDB_TIMEZONE = 42

# Construct the regular expression for a POSIX.1 timezone
posix_tz_name = r'[A-Z]{3,}'
posix_tz_offset = r'[+-]?\d+(:\d+(:\d+)?)?'
posix_tz_date = r'(J?\d+|M\d+\.\d+\.\d+)'
posix_timezone = r'^{std}{offset}({dst}({offset})?(,{start}(/{time})?,{end}(/{time})?)?)?$'.format(
    std=posix_tz_name,
    dst=posix_tz_name,
    offset=posix_tz_offset,
    time=posix_tz_offset,
    start=posix_tz_date,
    end=posix_tz_date
)
posix_timezone_re = re.compile(posix_timezone, re.IGNORECASE)


class PosixTimezoneOption(Option):
    """
    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |  OPTION_NEW_POSIX_TIMEZONE    |         option-length         |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                       TZ POSIX String                         |
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code:
        OPTION_NEW_POSIX_TIMEZONE(41)

    option-length:
        the number of octets of the TZ POSIX String Index described below:

    TZ POSIX string is a string suitable for the TZ variable as specified by IEEE 1003.1 in Section 8.3, with the
    exception that a string may not begin with a colon (":"). This string is NOT terminated by an ASCII NULL.

    Here is an example: EST5EDT4,M3.2.0/02:00,M11.1.0/02:00

    In this case, the string is interpreted as a timezone that is normally five hours behind UTC, and four hours behind
    UTC during DST, which runs from the second Sunday in March at 02:00 local time through the first Sunday in November
    at 02:00 local time. Normally the timezone is abbreviated "EST" but during DST it is abbreviated "EDT".

    Clients and servers implementing other timezone options MUST support this option for basic compatibility.
    """

    option_type = OPTION_NEW_POSIX_TIMEZONE

    def __init__(self, timezone: str = None):
        self.timezone = timezone

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.timezone, str):
            raise ValueError("Timezone must be a string")

        if len(self.timezone) > 65535:
            raise ValueError("Timezone must be 65535 characters or less")

        if self.timezone.startswith(':'):
            raise ValueError("Timezone descriptions starting with a colon are not allowed")

        if not posix_timezone_re.match(self.timezone):
            raise ValueError("Timezone description does not conform to POSIX.1")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may
        contain more data after the structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        self.timezone = buffer[offset + my_offset:offset + my_offset + option_len].decode('ascii')
        my_offset += option_len

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.timezone)))
        buffer.extend(self.timezone.encode('ascii'))
        return buffer


class TZDBTimezoneOption(Option):
    """
    .. code-block:: none

       0                   1                   2                   3
       0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |  OPTION_NEW_TZDB_TIMEZONE     |          option-length        |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
      |                            TZ Name                            |
      |                              ...                              |
      +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    option-code:
        OPTION_NEW_TZDB_TIMEZONE(42)

    option-length:
        the number of octets of the TZ Database String Index described below.

    TZ Name is the name of a Zone entry in the database commonly referred to as the TZ database. Specifically, in the
    database's textual form, the string refers to the name field of a zone line. In order for this option to be useful,
    the client must already have a copy of the database. This string is NOT terminated with an ASCII NULL.

    An example string is: Europe/Zurich.

    Clients must already have a copy of the TZ Database for this option to be useful. Configuration of the database is
    beyond the scope of this document. A client that supports this option SHOULD prefer this option to POSIX string if
    it recognizes the TZ Name that was returned. If it doesn't recognize the TZ Name, the client MUST ignore this
    option.
    """
    option_type = OPTION_NEW_TZDB_TIMEZONE

    def __init__(self, timezone: str = None):
        self.timezone = timezone

    def validate(self):
        """
        Validate that the contents of this object conform to protocol specs.
        """
        if not isinstance(self.timezone, str):
            raise ValueError("Timezone must be a string")

        if len(self.timezone) > 65535:
            raise ValueError("Timezone must be 65535 characters or less")

        if not all(c in string.printable for c in self.timezone):
            raise ValueError("Timezone must contain only printable ASCII characters")

    def load_from(self, buffer: bytes, offset: int = 0, length: int = None) -> int:
        """
        Load the internal state of this object from the given buffer. The buffer may
        contain more data after the structured element is parsed. This data is ignored.

        :param buffer: The buffer to read data from
        :param offset: The offset in the buffer where to start reading
        :param length: The amount of data we are allowed to read from the buffer
        :return: The number of bytes used from the buffer
        """
        my_offset, option_len = self.parse_option_header(buffer, offset, length)

        self.timezone = buffer[offset + my_offset:offset + my_offset + option_len].decode('ascii')
        my_offset += option_len

        return my_offset

    def save(self) -> Union[bytes, bytearray]:
        """
        Save the internal state of this object as a buffer.

        :return: The buffer with the data from this element
        """
        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.timezone)))
        buffer.extend(self.timezone.encode('ascii'))
        return buffer


SolicitMessage.add_may_contain(PosixTimezoneOption, 0, 1)
AdvertiseMessage.add_may_contain(PosixTimezoneOption, 0, 1)
RequestMessage.add_may_contain(PosixTimezoneOption, 0, 1)
RenewMessage.add_may_contain(PosixTimezoneOption, 0, 1)
RebindMessage.add_may_contain(PosixTimezoneOption, 0, 1)
InformationRequestMessage.add_may_contain(PosixTimezoneOption, 0, 1)
ReplyMessage.add_may_contain(PosixTimezoneOption, 0, 1)

SolicitMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
AdvertiseMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
RequestMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
RenewMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
RebindMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
InformationRequestMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
ReplyMessage.add_may_contain(TZDBTimezoneOption, 0, 1)
