"""
Handler that implements rapid-commit on the server.
"""
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, STATUS_NO_PREFIX_AVAIL
from dhcpkit.ipv6.messages import AdvertiseMessage, ReplyMessage, SolicitMessage
from dhcpkit.ipv6.options import IANAOption, IATAOption, RapidCommitOption, STATUS_NO_ADDRS_AVAIL, StatusCodeOption
from dhcpkit.ipv6.server.handlers import Handler
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


class RapidCommitHandler(Handler):
    """
    Upgrade AdvertiseMessage to ReplyMessage when client asks for rapid-commit
    """

    def __init__(self, rapid_commit_rejections: bool):
        super().__init__()

        self.rapid_commit_rejections = rapid_commit_rejections
        """
        Do rapid-commit when an IA_NA, IA_TA or IA_PD request gets refused. We have seen at lease one
        vice (Fritz!Box) that gets confused when a rapid-commit message tells it there are no addresses
        available. Turning this setting off works around that problem by not doing a rapid-commit when
        something gets refused.
        """

    def handle(self, bundle: TransactionBundle):
        """
        Don't do anything, all the processing happens in :meth:`post`.

        :param bundle: The transaction bundle
        """

    def post(self, bundle: TransactionBundle):
        """
        Upgrade the response from a AdvertiseMessage to a ReplyMessage if appropriate
        :param bundle: The transaction bundle
        """
        # Does this transaction even allow rapid commit?
        if not bundle.allow_rapid_commit:
            return

        # We only look for SolicitMessages that have a RapidCommitOption
        if not isinstance(bundle.request, SolicitMessage) or not bundle.request.get_option_of_type(RapidCommitOption):
            return

        # And only if the current response is an AdvertiseMessage
        if not isinstance(bundle.response, AdvertiseMessage):
            return

        # Ok, this looks promising, do extra checks if requested
        if not self.rapid_commit_rejections:
            # Ok, we don't want to rapid-commit rejections. Check for them.
            if bundle.get_unhandled_options((IANAOption, IATAOption, IAPDOption)):
                # Unhandled options. We are post-processing, so they are not going to be answered anymore
                return

            # Did we already refuse anything?
            ia_options = [option for option in bundle.response.options if isinstance(option, (IANAOption, IATAOption))]
            for option in ia_options:
                status = option.get_option_of_type(StatusCodeOption)
                if status and status.status_code == STATUS_NO_ADDRS_AVAIL:
                    # Refusal: don't do anything
                    return

            iapd_options = [option for option in bundle.response.options if isinstance(option, IAPDOption)]
            for option in iapd_options:
                status = option.get_option_of_type(StatusCodeOption)
                if status and status.status_code == STATUS_NO_PREFIX_AVAIL:
                    # Refusal: don't do anything
                    return

        # It seems the request and response qualify: upgrade to ReplyMessage
        bundle.response = ReplyMessage(bundle.response.transaction_id, [RapidCommitOption()] + bundle.response.options)
