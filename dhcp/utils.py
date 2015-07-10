import re


def camelcase_to_underscore(camelcase: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camelcase)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def camelcase_to_dash(camelcase: str) -> str:
    return camelcase_to_underscore(camelcase).replace('_', '-')


# Representation and Use of Domain Names
# https://tools.ietf.org/html/rfc3315#section-8
#
# So that domain names may be encoded uniformly, a domain name or a
# list of domain names is encoded using the technique described in
# section 3.1 of RFC 1035 [10].  A domain name, or list of domain
# names, in DHCP MUST NOT be stored in compressed form, as described in
# section 4.1.4 of RFC 1035.
def parse_domain_name(buffer: bytes, offset: int=0, length: int=None) -> (int, str):
    """
    Extract a single domain name.

    :param buffer: The buffer to read data from
    :param offset: The offset in the buffer where to start reading
    :param length: The amount of data we are allowed to read from the buffer
    :return: The number of bytes used from the buffer and the extracted domain name
    """
    my_offset = 0
    max_offset = length

    current_labels = []
    while max_offset > my_offset:
        label_length = buffer[offset + my_offset]
        my_offset += 1

        # End of a sequence of labels
        if label_length == 0:
            domain_name = '.'.join(current_labels)
            return my_offset, domain_name

        if label_length > 63:
            raise ValueError('Domain List contains label with invalid length')

        # Check if we stay below the max offset
        if my_offset + label_length > max_offset:
            raise ValueError('Invalid encoded domain name, exceeds available space')

        # New label
        current_label_bytes = buffer[offset + my_offset:offset + my_offset + label_length]
        my_offset += label_length

        if not current_label_bytes.isalnum():
            raise ValueError('Domain labels must be alphanumerical')
        current_label = current_label_bytes.decode('ascii')
        current_labels.append(current_label)

    raise ValueError('Domain name must end with a 0-length label')


def parse_domain_names(buffer: bytes, offset: int=0, length: int=None) -> (int, list):
    """
    Extract a list of domain names.

    :param buffer: The buffer to read data from
    :param offset: The offset in the buffer where to start reading
    :param length: The amount of data we are allowed to read from the buffer
    :return: The number of bytes used from the buffer and the extracted domain names
    """
    my_offset = 0
    max_offset = length

    domain_names = []
    while max_offset > my_offset:
        domain_name_len, domain_name = parse_domain_name(buffer, offset=offset + my_offset, length=length - my_offset)
        domain_names.append(domain_name)
        my_offset += domain_name_len

    return my_offset, domain_names


def encode_domain_name(domain_name: str) -> bytes:
    buffer = bytearray()

    # Be nice: strip trailing dots
    domain_name = domain_name.rstrip('.')

    domain_name_parts = domain_name.split('.')
    for label in domain_name_parts:
        if not label.isalnum():
            raise ValueError('Domain labels must be alphanumerical')

        label_length = len(label)
        if label_length < 1 or label_length > 63:
            raise ValueError('Domain name contains label with invalid length')

        buffer.append(label_length)
        buffer.extend(label.encode('ascii'))

    # End the domain name with a 0-length label
    buffer.append(0)

    return buffer


def encode_domain_names(domain_names: [str]) -> bytes:
    buffer = bytearray()
    for domain_name in domain_names:
        buffer.extend(encode_domain_name(domain_name))
    return buffer
