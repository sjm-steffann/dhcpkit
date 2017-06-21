"""
Implementation of Echo Request option handling as specified in :rfc:`4994`.
"""
from typing import List

from dhcpkit.ipv6.extensions.relay_echo_request import EchoRequestOption
from dhcpkit.ipv6.messages import RelayForwardMessage, RelayReplyMessage
from dhcpkit.ipv6.server.handlers import Handler, RelayHandler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


def create_cleanup_handlers() -> List[Handler]:
    """
    Create handlers to clean up stuff in the transaction bundle

    :return: Handlers to add to the handler chain
    """
    return [RelayEchoRequestOptionHandler()]


class RelayEchoRequestOptionHandler(RelayHandler):
    """
    When a server creates a Relay-Reply, it SHOULD perform ERO processing
    after processing the ORO and other options processing.  For each
    option in the ERO:

    a.  If the option is already in the Relay-Reply, the server MUST
        ignore that option and continue to process any remaining options
        in the ERO.

    b.  If the option was not in the received Relay-Forward, the server
        MUST ignore that option and continue to process any remaining
        options in the ERO.

    c.  Otherwise, the server MUST copy the option, verbatim, from the
        received Relay-Forward to the Relay-Reply, even if the server
        does not otherwise recognize that option.
    """

    def handle_relay(self, bundle: TransactionBundle,
                     relay_message_in: RelayForwardMessage, relay_message_out: RelayReplyMessage):
        """
        Handle the options for each relay message pair.

        :param bundle: The transaction bundle
        :param relay_message_in: The incoming relay message
        :param relay_message_out: Thr outgoing relay message
        """
        # See if the relay message contains an ERO
        ero = relay_message_in.get_option_of_type(EchoRequestOption)
        if not ero:
            # Nothing to do
            return

        for option_type in ero.requested_options:
            # Don't do anything if the outgoing relay message already has this one
            if any(option.option_type == option_type for option in relay_message_out.options):
                continue

            # Get the incoming options of the requested type
            incoming_options = [option for option in relay_message_in.options if option.option_type == option_type]

            for option in incoming_options:
                # Make sure this option can go into this type of response
                if not relay_message_out.may_contain(option):
                    return

                # And append them to the outgoing message if possible
                relay_message_out.options.append(option)
