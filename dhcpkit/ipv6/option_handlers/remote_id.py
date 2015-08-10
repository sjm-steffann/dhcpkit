"""
Option handlers for the basic :rfc:`3315` options
"""
import configparser
import logging

from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.option_handlers import register_option_handler, CopyRelayOptionHandler, OptionHandler

logger = logging.getLogger(__name__)


class RemoteIdOptionHandler(CopyRelayOptionHandler):
    """
    The handler for RemoteIdOptions in relay messages
    """

    def __init__(self):
        super().__init__(RemoteIdOption)

    @classmethod
    def from_config(cls, section: configparser.SectionProxy, option_handler_id: str=None) -> OptionHandler:
        """
        Create a handler of this class based on the configuration in the config section.

        :param section: The configuration section
        :param option_handler_id: Optional extra identifier
        :return: A handler object
        :rtype: OptionHandler
        """
        # Don't look at the options, just add this option handler
        return cls()


register_option_handler(RemoteIdOptionHandler)
