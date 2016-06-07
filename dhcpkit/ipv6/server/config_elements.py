"""
The basic configuration objects
"""

import grp
import logging
import netifaces

import abc

from dhcpkit.ipv6.duids import LinkLayerDUID, DUID
from dhcpkit.utils import normalise_hex

logger = logging.getLogger(__name__)


class ConfigElementBase:
    """
    The configuration consists of multiple levels of filters, which contain the options that are applied to requests
    that match the filter condition. Filters make sure that at least subnet-based filters make a bit of sense.
    """

    def __init__(self, section):
        self._element = None
        self.section = section
        self.clean_config_section()
        self.validate_config_section()

    # noinspection PyMethodMayBeStatic
    def clean_config_section(self):
        """
        Clean up the config, calculating defaults etc.
        """

    # noinspection PyMethodMayBeStatic
    def validate_config_section(self):
        """
        Validate if the information in the config section is acceptable
        """

    def __str__(self) -> str:
        """
        Simple repr implementation to show the corresponding config

        :return: Config representation
        """
        return str(self.section)


class ConfigFactoryElement(ConfigElementBase, metaclass=abc.ABCMeta):
    """
    Base class for factories to create elements from configuration
    """

    @abc.abstractmethod
    def create(self) -> object:
        """
        Override this method to create the handler.

        :return: The option handler
        """
        return None

    def __call__(self) -> object:
        """
        Create the handler on demand and return it.

        :return: The option handler
        """
        # Create the handler if we haven't done so yet
        if self._element is None:
            self._element = self.create()

        return self._element


class MainConfig(ConfigElementBase):
    """
    The top level configuration element
    """

    def __init__(self, section):
        self.user = None
        self.group = None
        self.duid = None

        super().__init__(section)

    def clean_config_section(self):
        """
        Clean up the config, making sure we have user, group and DUID
        """
        if self.section.group is None:
            # No group specified
            try:
                self.section.group = grp.getgrgid(self.section.user.pw_gid)
            except KeyError:
                raise ValueError("User {} has a non-existent primary group {}".format(self.section.user.pw_name,
                                                                                      self.section.user.pw_gid))

        if not self.section.server_id:
            self.section.server_id = self.determine_server_duid()

    def determine_server_duid(self) -> DUID:
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
                    if len(ll_addr) != 6:
                        # If it is not 6 bytes long then it is not an ethernet MAC address
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
