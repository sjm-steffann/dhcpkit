from struct import unpack_from, pack
from ipaddress import IPv6Address

from dhcp.ipv6.messages import Message
from dhcp.ipv6.options import Option

OPTION_CLIENTID = 1
OPTION_SERVERID = 2
OPTION_IA_NA = 3
OPTION_IA_TA = 4
OPTION_IAADDR = 5
OPTION_ORO = 6
OPTION_PREFERENCE = 7
OPTION_ELAPSED_TIME = 8
OPTION_RELAY_MSG = 9
OPTION_AUTH = 11
OPTION_UNICAST = 12
OPTION_STATUS_CODE = 13
OPTION_RAPID_COMMIT = 14
OPTION_USER_CLASS = 15
OPTION_VENDOR_CLASS = 16
OPTION_VENDOR_OPTS = 17
OPTION_INTERFACE_ID = 18
OPTION_RECONF_MSG = 19
OPTION_RECONF_ACCEPT = 20


class ClientIdentifierOption(Option):
    def __init__(self, duid: bytes=b''):
        super().__init__()
        self.option_type = OPTION_CLIENTID
        self.duid = duid

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain a Client Identifier option')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.duid = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> bytes:
        return pack('!HH', self.option_type, len(self.duid)) + self.duid


Option.register_option_type(OPTION_CLIENTID, ClientIdentifierOption)


class ServerIdentifierOption(Option):
    def __init__(self, duid: bytes=b''):
        super().__init__()
        self.option_type = OPTION_SERVERID
        self.duid = duid

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain a Server Identifier option')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.duid = buffer[offset + my_offset:offset + my_offset + option_len]
        my_offset += option_len

        return my_offset

    def save(self) -> bytes:
        return pack('!HH', self.option_type, len(self.duid)) + self.duid


Option.register_option_type(OPTION_SERVERID, ServerIdentifierOption)


class IANAOption(Option):
    def __init__(self, iaid: bytes=b'\x00\x00\x00\x00', t1: int=0, t2: int=0, options: []=None):
        super().__init__()
        self.option_type = OPTION_IA_NA
        self.iaid = iaid
        self.t1 = t1
        self.t2 = t2
        self.options = options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain an Identity Association for '
                             'Non-temporary Addresses option')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.iaid = buffer[offset + my_offset:offset + my_offset + 4]
        my_offset += 4

        self.t1, self.t2 = unpack_from('!II', buffer, offset + my_offset)
        my_offset += 8

        # Parse the options
        max_offset = option_len + 4  # The option_len field counts bytes *after* the option_type and option_len field
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> bytes:
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH4sII', self.option_type, len(options_buffer) + 12, self.iaid, self.t1, self.t2))
        buffer.extend(options_buffer)
        return buffer


Option.register_option_type(OPTION_IA_NA, IANAOption)


class IATAOption(Option):
    def __init__(self, iaid: bytes=b'\x00\x00\x00\x00', options: []=None):
        super().__init__()
        self.option_type = OPTION_IA_TA
        self.iaid = iaid
        self.options = options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain an Identity Association for '
                             'Temporary Addresses option')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.iaid = buffer[offset + my_offset:offset + my_offset + 4]
        my_offset += 4

        # Parse the options
        max_offset = option_len + 4  # The option_len field counts bytes *after* the option_type and option_len field
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> bytes:
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH4s', self.option_type, len(options_buffer) + 12, self.iaid))
        buffer.extend(options_buffer)
        return buffer


Option.register_option_type(OPTION_IA_TA, IATAOption)


class IAAddressOption(Option):
    def __init__(self, address: IPv6Address=None, preferred_lifetime: int=0, valid_lifetime: int=0, options: []=None):
        super().__init__()
        self.option_type = OPTION_IAADDR
        self.address = address
        self.preferred_lifetime = preferred_lifetime
        self.valid_lifetime = valid_lifetime
        self.options = options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain an IA Address Option')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.address = IPv6Address(buffer[offset + my_offset:offset + my_offset + 16])
        my_offset += 16

        self.preferred_lifetime, self.valid_lifetime = unpack_from('!II', buffer, offset + my_offset)
        my_offset += 8

        # Parse the options
        max_offset = option_len + 4  # The option_len field counts bytes *after* the option_type and option_len field
        while max_offset > my_offset:
            used_buffer, option = Option.parse(buffer, offset=offset + my_offset)
            self.options.append(option)
            my_offset += used_buffer

        if my_offset != max_offset:
            raise ValueError('Option length does not match the combined length of the parsed options')

        return my_offset

    def save(self) -> bytes:
        options_buffer = bytearray()
        for option in self.options:
            options_buffer.extend(option.save())

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(options_buffer) + 24))
        buffer.extend(self.address.packed)
        buffer.extend(pack('!II', self.preferred_lifetime, self.valid_lifetime))
        buffer.extend(options_buffer)
        return buffer


Option.register_option_type(OPTION_IAADDR, IAAddressOption)


class OptionRequestOption(Option):
    def __init__(self, requested_options: []=None):
        super().__init__()
        self.option_type = OPTION_ORO
        self.requested_options = requested_options or []

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain an Option Request Option')

        if option_len % 2 != 0:
            raise ValueError('Invalid option length')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.requested_options = list(unpack_from('!{}H'.format(option_len // 2), buffer, offset + my_offset))
        my_offset += option_len

        return my_offset

    def save(self) -> bytes:
        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(self.requested_options) * 2))
        buffer.extend(pack('!{}H'.format(len(self.requested_options)), *self.requested_options))
        return buffer


Option.register_option_type(OPTION_ORO, OptionRequestOption)


class PreferenceOption(Option):
    def __init__(self, preference: int=0):
        super().__init__()
        self.option_type = OPTION_PREFERENCE
        self.preference = preference

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain a Preference Option')

        if option_len != 1:
            raise ValueError('Invalid option length')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.preference = buffer[offset + my_offset]
        my_offset += 1

        return my_offset

    def save(self) -> bytes:
        return pack('!HHB', self.option_type, 1, self.preference)


Option.register_option_type(OPTION_PREFERENCE, PreferenceOption)


class ElapsedTimeOption(Option):
    def __init__(self, elapsed_time: int=0):
        super().__init__()
        self.option_type = OPTION_ELAPSED_TIME
        self.elapsed_time = elapsed_time

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain an Elapsed Time Option')

        if option_len != 2:
            raise ValueError('Invalid option length')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        self.elapsed_time = unpack_from('!H', buffer, offset=offset + my_offset)[0]
        my_offset += 2

        return my_offset

    def save(self) -> bytes:
        return pack('!HHH', self.option_type, 2, self.elapsed_time)


Option.register_option_type(OPTION_ELAPSED_TIME, ElapsedTimeOption)


class RelayMessageOption(Option):
    def __init__(self, relayed_message: Message=None):
        super().__init__()
        self.option_type = OPTION_RELAY_MSG
        self.relayed_message = relayed_message

    def load_from(self, buffer: bytes, offset: int=0, length: int=None) -> int:
        my_offset = 0

        option_type, option_len = unpack_from('!HH', buffer, offset=offset + my_offset)
        my_offset += 4

        if option_type != self.option_type:
            raise ValueError('The provided buffer does not contain an Relay Message Option')

        max_length = length or (len(buffer) - offset)
        if my_offset + option_len > max_length:
            raise ValueError('This option is longer than the available buffer')

        message_len, self.relayed_message = Message.parse(buffer, offset=offset + my_offset, length=option_len)
        my_offset += option_len

        if message_len != option_len:
            raise ValueError('The embedded message has a different length than the Relay Message Option', message_len,
                             option_len)

        return my_offset

    def save(self) -> bytes:
        message = self.relayed_message.save()

        buffer = bytearray()
        buffer.extend(pack('!HH', self.option_type, len(message)))
        buffer.extend(message)
        return buffer


Option.register_option_type(OPTION_RELAY_MSG, RelayMessageOption)
