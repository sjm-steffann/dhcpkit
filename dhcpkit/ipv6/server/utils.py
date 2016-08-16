"""
Utility functions for the DHCP server
"""
import logging
import netifaces

from dhcpkit.ipv6.duids import LinkLayerDUID
from dhcpkit.utils import normalise_hex

logger = logging.getLogger(__name__)


def determine_local_duid() -> LinkLayerDUID:
    """
    Calculate our own DUID based on one of our MAC addresses

    :return: The server DUID
    """
    for interface_name in netifaces.interfaces():
        link_addresses = netifaces.ifaddresses(interface_name).get(netifaces.AF_LINK, [])
        link_addresses = [link_address['addr'] for link_address in link_addresses if link_address.get('addr')]

        for link_address in link_addresses:
            try:
                # Build a DUID from this address
                ll_addr = bytes.fromhex(normalise_hex(link_address))
                if len(ll_addr) != 6 or ll_addr == b'\x00\x00\x00\x00\x00\x00':
                    # If it is not 6 bytes long then it is not an ethernet MAC address, and all-zeroes is just a fake
                    continue

                # Assume it's ethernet, build a DUID
                duid = LinkLayerDUID(hardware_type=1, link_layer_address=ll_addr)

                logger.debug("Using server DUID based on {} link address: {}".format(interface_name, link_address))

                return duid
            except ValueError:
                # Try the next one
                pass

    # We didn't find a useful server DUID
    raise ValueError("Cannot find a usable server DUID")
