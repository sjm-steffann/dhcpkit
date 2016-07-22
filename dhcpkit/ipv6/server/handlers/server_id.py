"""
Handlers for the basic :rfc:`3315` options
"""

import logging

from dhcpkit.ipv6.duids import DUID
from dhcpkit.ipv6.options import ServerIdOption
from dhcpkit.ipv6.server.handlers import CannotRespondError
from dhcpkit.ipv6.server.handlers.basic import OverwriteOptionHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle

logger = logging.getLogger(__name__)


class ForOtherServerError(CannotRespondError):
    """
    A specific case of being unable to respond: this message is for another server
    """
    pass


class ServerIdHandler(OverwriteOptionHandler):
    """
    The handler for ServerIdOption. Checks whether any server-id in the request matches our own and puts our server-id
    in the response message to let the client know who is answering.

    :type option: ServerIdOption
    """

    option = None

    def __init__(self, duid: DUID):
        """
        Create a handler function based on the provided DUID

        :param duid: The DUID of this server
        """
        option = ServerIdOption(duid)
        option.validate()

        super().__init__(option, always_send=True)

    def pre(self, bundle: TransactionBundle):
        """
        Check if there is a ServerId in the request

        :param bundle: The transaction bundle
        """
        server_id = bundle.request.get_option_of_type(ServerIdOption)
        if server_id and server_id.duid != self.option.duid:
            # This message is not for this server
            raise ForOtherServerError
