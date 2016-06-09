"""
The basic configuration objects
"""

import grp
import logging

from ZConfig.matcher import SectionValue

from dhcpkit.common.server.config_elements import ConfigSection
from dhcpkit.ipv6.server.utils import determine_local_duid

logger = logging.getLogger(__name__)


class MainConfig(ConfigSection):
    """
    The top level configuration element
    """

    def __init__(self, section: SectionValue):
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
            self.section.server_id = determine_local_duid()
