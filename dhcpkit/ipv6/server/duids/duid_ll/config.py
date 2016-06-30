"""
Configuration section for LinkLayerDUID
"""
import logging

from dhcpkit.ipv6.duids import LinkLayerDUID

logger = logging.getLogger(__name__)


def duid_ll(section) -> LinkLayerDUID:
    """
    Create a LinkLayerDUID from the data provided in the config section.

    :param section: The section data
    :return: The DUID object
    """
    duid = LinkLayerDUID(hardware_type=section.hardware_type,
                         link_layer_address=section.link_layer_address)
    duid.validate()
    return duid
