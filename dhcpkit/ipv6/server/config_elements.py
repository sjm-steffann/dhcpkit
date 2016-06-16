"""
The basic configuration objects
"""

import grp
import logging
import pwd

from dhcpkit.common.server.config_elements import ConfigSection
from dhcpkit.common.server.logging.config_elements import Logging
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
        if self._section.group is None:
            # No group specified
            try:
                self._section.group = grp.getgrgid(self._section.user.pw_gid)
            except KeyError:
                raise ValueError("User {} has a non-existent primary group {}".format(self._section.user.pw_name,
                                                                                      self._section.user.pw_gid))

        if not self._section.server_id:
            self._section.server_id = determine_local_duid()

    @property
    def logging(self) -> Logging:
        """
        Shortcut to the logging configuration.

        :return: Logging configuration
        """
        return self._section.logging

    @property
    def user(self) -> pwd.struct_passwd:
        """
        Shortcut to the user configuration.

        :return: User configuration
        """
        return self._section.user

    @property
    def group(self) -> grp.struct_group:
        """
        Shortcut to the group configuration.

        :return: Group configuration
        """
        return self._section.group

    def create_message_handler(self) -> MessageHandler:
        """
        Create a message handler based on this configuration.

        :return: The message handler
        """
        sub_filters = []
        for filter_factory in self._section.filter_factories:
            sub_filters.append(filter_factory())

        sub_handlers = []
        for handler_factory in self._section.handler_factories:
            sub_handlers.append(handler_factory())

        return MessageHandler(self._section.server_id, sub_filters, sub_handlers, self._section.allow_rapid_commit)
