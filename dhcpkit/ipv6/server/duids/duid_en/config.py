"""
Configuration section for EnterpriseDUID
"""
import logging

from dhcpkit.ipv6.duids import EnterpriseDUID

logger = logging.getLogger(__name__)


def duid_en(section) -> EnterpriseDUID:
    """
    Create a EnterpriseDUID from the data provided in the config section.

    :param section: The section data
    :return: The DUID object
    """
    duid = EnterpriseDUID(enterprise_number=section.enterprise_number,
                          identifier=section.identifier)
    duid.validate()
    return duid
