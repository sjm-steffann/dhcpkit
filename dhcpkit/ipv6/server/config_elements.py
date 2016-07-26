"""
The basic configuration objects
"""

import grp
import logging

from dhcpkit.common.server.config_elements import ConfigSection
from dhcpkit.ipv6.server.message_handler import MessageHandler
from dhcpkit.ipv6.server.utils import determine_local_duid

logger = logging.getLogger(__name__)


class MainConfig(ConfigSection):
    """
    The top level configuration element
    """

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
            self.section.server_id = determine_local_duid()

    def create_message_handler(self) -> MessageHandler:
        """
        Create a message handler based on this configuration.

        :return: The message handler
        """
        sub_filters = []
        for filter_factory in self.section.filter_factories:
            sub_filters.append(filter_factory())

        sub_handlers = []
        for handler_factory in self.section.handler_factories:
            sub_handlers.append(handler_factory())

        return MessageHandler(self.section.server_id, sub_filters, sub_handlers, self.section.allow_rapid_commit)


class StatisticsConfig(ConfigSection):
    """
    Configuration of the statistics gatherer
    """
