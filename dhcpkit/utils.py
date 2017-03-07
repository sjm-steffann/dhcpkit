"""
Utility functions
"""
import codecs
import re

from typing import Iterable, Tuple


def camelcase_to_underscore(camelcase: str) -> str:
    """
    Convert a name in CamelCase to non_camel_case

    :param camelcase: CamelCased string
    :return: non_camel_cased string
    """
    # Handle weird Camel-Case notation
    s0 = camelcase.replace('-', '_')

    # Insert an underscore before any uppercase letter which is followed by a lowercase letter
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s0)

    # Insert an underscore before any uppercase letter which is preceded by a lowercase letter or number
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)

    # Lowercase the result
    s3 = s2.lower()

    # And return with double underscores collapsed
    return re.sub(r'_+', '_', s3)


def camelcase_to_dash(camelcase: str) -> str:
    """
    Convert a name in CamelCase to non-camel-case

    :param camelcase: CamelCased string
    :return: non-camel-cased string
    """
    # The same as camelcase_to_underscore, but with the underscores replaced by dashes
    return camelcase_to_underscore(camelcase).replace('_', '-')


def validate_domain_label(label: str):
    """
    Check if a given string is a valid domain label

    :param label: The domain label
    """
    label_length = len(label)
    if 1 > label_length > 63:
        raise ValueError('Domain labels must be 1 to 63 characters long')

    if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', label, re.IGNORECASE):
        raise ValueError('Domain labels must consist of letters, digits and hyphens, '
                         'and may not begin or end with a hyphen')


# Representation and Use of Domain Names
# :rfc:`3315#section-8`
#
# So that domain names may be encoded uniformly, a domain name or a
# list of domain names is encoded using the technique described in
# section 3.1 of :rfc:`1035` [10].  A domain name, or list of domain
# names, in DHCP MUST NOT be stored in compressed form, as described in
# section 4.1.4 of :rfc:`1035`.
def parse_domain_bytes(buffer: bytes, offset: int = 0, length: int = None,
                       allow_relative: bool = False) -> Tuple[int, str]:
    """
    Extract a single domain name.

    :param buffer: The buffer to read data from
    :param offset: The offset in the buffer where to start reading
    :param length: The amount of data we are allowed to read from the buffer
    :param allow_relative: Allow domain names that do not end with a zero-length label
    :return: The number of bytes used from the buffer and the extracted domain name
    """
    my_offset = 0
    max_offset = length or (len(buffer) - offset)

    current_labels = []
    while max_offset > my_offset:
        label_length = buffer[offset + my_offset]
        my_offset += 1

        # End of a sequence of labels
        if label_length == 0:
            domain_name_bytes = b'.'.join(current_labels) + b'.'
            domain_name = codecs.decode(domain_name_bytes, 'idna')
            if len(domain_name) > 255:
                raise ValueError("Domain names must be 255 characters or less")
            return my_offset, domain_name

        if label_length > 63:
            raise ValueError('Domain labels must be 1 to 63 characters long')

        # Check if we stay below the max offset
        if my_offset + label_length > max_offset:
            raise ValueError('Invalid encoded domain name, exceeds available buffer')

        # New label
        current_label_bytes = buffer[offset + my_offset:offset + my_offset + label_length]
        my_offset += label_length

        current_labels.append(current_label_bytes)

    if allow_relative:
        # We have reached the end of the data and we allow relative labels: we're done
        domain_name_bytes = b'.'.join(current_labels)
        domain_name = codecs.decode(domain_name_bytes, 'idna')
        if len(domain_name) > 255:
            raise ValueError("Domain names must be 255 characters or less")
        return my_offset, domain_name

    raise ValueError('Domain name must end with a 0-length label')


def parse_domain_list_bytes(buffer: bytes, offset: int = 0, length: int = None) -> Tuple[int, list]:
    """
    Extract a list of domain names.

    :param buffer: The buffer to read data from
    :param offset: The offset in the buffer where to start reading
    :param length: The amount of data we are allowed to read from the buffer
    :return: The number of bytes used from the buffer and the extracted domain names
    """
    my_offset = 0
    max_offset = length or (len(buffer) - offset)

    domain_names = []
    while max_offset > my_offset:
        domain_name_len, domain_name = parse_domain_bytes(buffer,
                                                          offset=offset + my_offset, length=max_offset - my_offset)
        domain_names.append(domain_name)
        my_offset += domain_name_len

    return my_offset, domain_names


def encode_domain(domain_name: str, allow_relative: bool = False) -> bytearray:
    """
    Encode a single domain name as a sequence of bytes

    :param domain_name: The domain name
    :param allow_relative: Assume that domain names that don't end with a period are relative and encode them as such
    :return: The encoded domain name as bytes
    """
    if not isinstance(domain_name, str):
        raise ValueError("Domain name must be a string")

    buffer = bytearray()

    # Be nice: strip trailing dots
    if allow_relative:
        if domain_name.endswith('.'):
            # Treat as FQDN
            domain_name = domain_name.rstrip('.')
            end_with_zero = True
        else:
            # Treat as relative
            end_with_zero = False
    else:
        # Treat as fqdn
        domain_name = domain_name.rstrip('.')
        end_with_zero = True

    # Support IDN
    try:
        domain_name = codecs.encode(domain_name, 'idna').decode('ascii')
    except UnicodeError as e:
        if isinstance(e.__cause__, UnicodeError) and 'label' in e.__cause__.args[0]:
            raise ValueError('Domain labels must be 1 to 63 characters long')
        else:
            raise ValueError('Invalid domain name')

    if len(domain_name) > 255:
        raise ValueError("Domain names must be 255 characters or less")

    domain_name_parts = domain_name.split('.')
    for label in domain_name_parts:
        validate_domain_label(label)

        label_length = len(label)
        buffer.append(label_length)
        buffer.extend(label.encode('ascii'))

    if end_with_zero:
        # End FQDN domain name with a 0-length label
        buffer.append(0)

    return buffer


def encode_domain_list(domain_names: Iterable[str]) -> bytearray:
    """
    Encode a list of domain names to a sequence of bytes

    :param domain_names: The list of domain names
    :return: The encoded domain names as bytes
    """
    buffer = bytearray()
    for domain_name in domain_names:
        buffer.extend(encode_domain(domain_name))
    return buffer


def normalise_hex(hex_data: str, include_colons: bool = False) -> str:
    """
    Normalise a string containing hexadecimal data

    :param hex_data: Hexadecimal data, either with or without colon separators per byte
    :param include_colons: Whether to include colon separators per byte in the output
    :return: Hexadecimal data in lowercase without colon separators
    """
    # Empty strings are ok
    if hex_data == '':
        return hex_data

    # The rest needs to consist of sets of 2 hex characters, possibly separated with a colon
    if re.match(r'^[0-9A-Fa-f]{2}(:?[0-9A-Fa-f]{2})*$', hex_data):
        # Format is sane, strip any colons and lowercase, and we're done
        hex_data = hex_data.replace(':', '').lower()

        if include_colons:
            hex_data = ':'.join(re.findall('..', hex_data))

        return hex_data

    # Bad data
    raise ValueError('Input data is not valid hex data')
