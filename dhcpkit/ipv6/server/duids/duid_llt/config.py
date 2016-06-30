"""
Configuration section for LinkLayerTimeDUID
"""
import logging

from dhcpkit.ipv6.duids import LinkLayerTimeDUID

logger = logging.getLogger(__name__)


def duid_llt(section) -> LinkLayerTimeDUID:
    """
    Create a LinkLayerDUID from the data provided in the config section.

    :param section: The section data
    :return: The DUID object
    """
    duid = LinkLayerTimeDUID(hardware_type=section.hardware_type,
                             link_layer_address=section.link_layer_address,
                             time=section.timestamp)
    duid.validate()
    return duid
