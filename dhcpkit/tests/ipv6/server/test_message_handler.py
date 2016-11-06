"""
Testing of the message handler
"""
import logging
import unittest
from ipaddress import IPv6Address
from unittest.mock import call

from dhcpkit.ipv6.duids import LinkLayerTimeDUID
from dhcpkit.ipv6.extensions.prefix_delegation import IAPDOption, STATUS_NO_PREFIX_AVAIL
from dhcpkit.ipv6.messages import AdvertiseMessage, ClientServerMessage, ConfirmMessage, RelayForwardMessage, \
    ReplyMessage
from dhcpkit.ipv6.options import ClientIdOption, IANAOption, STATUS_NOT_ON_LINK, STATUS_NO_ADDRS_AVAIL, \
    STATUS_USE_MULTICAST, ServerIdOption, StatusCodeOption
from dhcpkit.ipv6.server.extension_registry import server_extension_registry
from dhcpkit.ipv6.server.filters.marks.config import MarkedWithFilter
from dhcpkit.ipv6.server.handlers import Handler, UseMulticastError
from dhcpkit.ipv6.server.handlers.ignore import IgnoreRequestHandler
from dhcpkit.ipv6.server.handlers.unicast import ServerUnicastOptionHandler
from dhcpkit.ipv6.server.message_handler import MessageHandler
from dhcpkit.ipv6.server.statistics import StatisticsSet
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle
from dhcpkit.tests import DeepCopyMagicMock
from dhcpkit.tests.ipv6.messages.test_confirm_message import confirm_message
from dhcpkit.tests.ipv6.messages.test_request_message import request_message
from dhcpkit.tests.ipv6.messages.test_solicit_message import solicit_message


class DummyMarksHandler(Handler):
    """
    A handler that sets marks in each of the phases of message handling
    """

    def __init__(self, mark: str):
        self.mark = mark
        super().__init__()

    def pre(self, bundle: TransactionBundle):
        """
        Add a mark to show we have been here
        """
        bundle.marks.add('pre-' + self.mark)

    def handle(self, bundle: TransactionBundle):
        """
        Add a mark to show we have been here
        """
        bundle.marks.add('handle-' + self.mark)

    def post(self, bundle: TransactionBundle):
        """
        Add a mark to show we have been here
        """
        bundle.marks.add('post-' + self.mark)


class BadExceptionHandler(Handler):
    """
    A handler that raises a bogus exception
    """

    def pre(self, bundle: TransactionBundle):
        """
        Raise UseMulticastError on multicast messages... This is intentionally wrong.
        """
        if bundle.received_over_multicast:
            raise UseMulticastError("Oops, we shouldn't raise this for multicast requests...")


class DummyExtension:
    """
    A server extension that adds the DummyMarksHandler at both setup and cleanup
    """

    @staticmethod
    def create_setup_handlers():
        """
        Add the DummyMarksHandler at setup
        """
        return [DummyMarksHandler('setup')]

    @staticmethod
    def create_cleanup_handlers():
        """
        Add the DummyMarksHandler at cleanup
        """
        return [DummyMarksHandler('cleanup')]


class MessageHandlerTestCase(unittest.TestCase):
    def setUp(self):
        # Add a dummy extensions that modifies the marks
        server_extension_registry['dummy'] = DummyExtension()

        # Some mock objects to use
        self.dummy_handler = DeepCopyMagicMock(spec=Handler)
        unicast_me_filter = MarkedWithFilter(filter_condition='unicast-me',
                                             sub_handlers=[ServerUnicastOptionHandler(
                                                 address=IPv6Address('2001:db8::1')
                                             )])
        ignore_me_filter = MarkedWithFilter(filter_condition='ignore-me', sub_handlers=[IgnoreRequestHandler()])
        reject_me_filter = MarkedWithFilter(filter_condition='reject-me', sub_handlers=[BadExceptionHandler()])

        # Prove to PyCharm that this is really a handler
        self.assertIsInstance(self.dummy_handler, Handler)

        # This is the DUID that is used in the message fixtures
        self.duid = LinkLayerTimeDUID(hardware_type=1, time=488458703, link_layer_address=bytes.fromhex('00137265ca42'))

        # Create some message handlers
        self.message_handler = MessageHandler(server_id=self.duid,
                                              sub_filters=[unicast_me_filter, ignore_me_filter, reject_me_filter],
                                              sub_handlers=[self.dummy_handler],
                                              allow_rapid_commit=False,
                                              rapid_commit_rejections=False)
        self.rapid_message_handler = MessageHandler(server_id=self.duid,
                                                    sub_handlers=[self.dummy_handler],
                                                    allow_rapid_commit=True,
                                                    rapid_commit_rejections=False)
        self.very_rapid_message_handler = MessageHandler(server_id=self.duid,
                                                         sub_handlers=[self.dummy_handler],
                                                         allow_rapid_commit=True,
                                                         rapid_commit_rejections=True)

    def test_worker_init(self):
        self.message_handler.worker_init()
        self.dummy_handler.assert_has_calls([
            call.worker_init()
        ])

    def test_empty_message(self):
        with self.assertLogs(level=logging.WARNING) as cm:
            bundle = TransactionBundle(incoming_message=RelayForwardMessage(),
                                       received_over_multicast=True)
            result = self.message_handler.handle(bundle, StatisticsSet())
            self.assertIsNone(result)

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], '^WARNING:.*:A server should not receive')

    def test_ignorable_multicast_message(self):
        with self.assertLogs(level=logging.DEBUG) as cm:
            bundle = TransactionBundle(incoming_message=solicit_message,
                                       received_over_multicast=True,
                                       marks=['ignore-me'])
            self.message_handler.handle(bundle, StatisticsSet())
            result = bundle.outgoing_message
            self.assertIsNone(result)

        self.assertEqual(len(cm.output), 3)
        self.assertRegex(cm.output[0], '^DEBUG:.*:Handling SolicitMessage')
        self.assertRegex(cm.output[1], '^INFO:.*:Configured to ignore SolicitMessage')
        self.assertRegex(cm.output[2], '^WARNING:.*:.*ignoring')

    def test_reject_unicast_message(self):
        with self.assertLogs(level=logging.DEBUG) as cm:
            bundle = TransactionBundle(incoming_message=solicit_message,
                                       received_over_multicast=False)
            self.message_handler.handle(bundle, StatisticsSet())
            result = bundle.outgoing_message
            self.assertIsInstance(result, ReplyMessage)
            self.assertEqual(result.get_option_of_type(StatusCodeOption).status_code, STATUS_USE_MULTICAST)

        self.assertEqual(len(cm.output), 3)
        self.assertRegex(cm.output[0], '^DEBUG:.*:Handling SolicitMessage')
        self.assertRegex(cm.output[1], '^INFO:.*:Rejecting unicast SolicitMessage')
        self.assertRegex(cm.output[2], '^DEBUG:.*:.*multicast is required')

    def test_accept_unicast_message(self):
        bundle = TransactionBundle(incoming_message=solicit_message,
                                   received_over_multicast=False,
                                   marks=['unicast-me'])
        self.message_handler.handle(bundle, StatisticsSet())
        result = bundle.outgoing_message
        self.assertIsInstance(result, AdvertiseMessage)
        self.assertIsNone(result.get_option_of_type(StatusCodeOption))

    def test_badly_rejected_multicast_message(self):
        with self.assertLogs(level=logging.DEBUG) as cm:
            bundle = TransactionBundle(incoming_message=solicit_message,
                                       received_over_multicast=True,
                                       marks=['reject-me'])
            self.message_handler.handle(bundle, StatisticsSet())
            result = bundle.outgoing_message
            self.assertIsNone(result)

        self.assertEqual(len(cm.output), 3)
        self.assertRegex(cm.output[0], '^DEBUG:.*:Handling SolicitMessage')
        self.assertRegex(cm.output[1], '^DEBUG:.*:.*multicast is required')
        self.assertRegex(cm.output[2], '^ERROR:.*:Not telling client to use multicast')

    def test_solicit_message(self):
        bundle = TransactionBundle(incoming_message=solicit_message,
                                   received_over_multicast=True,
                                   marks=['one', 'two', 'one'])
        self.message_handler.handle(bundle, StatisticsSet())
        result = bundle.outgoing_message

        self.assertIsInstance(result, AdvertiseMessage)
        self.assertEqual(result.transaction_id, solicit_message.transaction_id)
        self.assertEqual(result.get_option_of_type(ClientIdOption), solicit_message.get_option_of_type(ClientIdOption))
        self.assertEqual(result.get_option_of_type(ServerIdOption).duid, self.duid)
        self.assertEqual(result.get_option_of_type(IANAOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_ADDRS_AVAIL)
        self.assertEqual(result.get_option_of_type(IAPDOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_PREFIX_AVAIL)

        # Check if the handlers are called correctly
        for method_name in ['pre', 'handle', 'post']:
            method = getattr(self.dummy_handler, method_name)

            self.assertEqual(method.call_count, 1)
            args, kwargs = method.call_args
            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)
            self.assertIsInstance(args[0], TransactionBundle)

        # Check the types and values at various stages
        # In the pre phase there is no response yet
        bundle = self.dummy_handler.pre.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one', 'two',
                                        'pre-setup'})
        self.assertIsNone(bundle.response)
        self.assertIsNone(bundle.outgoing_relay_messages)

        # In the handle phase there is an AdvertiseMessage
        bundle = self.dummy_handler.handle.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one', 'two',
                                        'pre-setup', 'pre-cleanup',
                                        'handle-setup'})
        self.assertIsInstance(bundle.response, AdvertiseMessage)
        self.assertEqual(bundle.outgoing_relay_messages, [])

        # In the post phase there is still an AdvertiseMessage (no rapid commit)
        bundle = self.dummy_handler.post.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one', 'two',
                                        'pre-setup', 'pre-cleanup',
                                        'handle-setup', 'handle-cleanup',
                                        'post-setup'})
        self.assertIsInstance(bundle.response, AdvertiseMessage)
        self.assertEqual(bundle.outgoing_relay_messages, [])

    def test_rapid_solicit_message(self):
        bundle = TransactionBundle(incoming_message=solicit_message,
                                   received_over_multicast=True,
                                   marks=['one', 'two'])
        self.rapid_message_handler.handle(bundle, StatisticsSet())
        result = bundle.outgoing_message

        self.assertIsInstance(result, AdvertiseMessage)
        self.assertEqual(result.transaction_id, solicit_message.transaction_id)
        self.assertEqual(result.get_option_of_type(ClientIdOption), solicit_message.get_option_of_type(ClientIdOption))
        self.assertEqual(result.get_option_of_type(ServerIdOption).duid, self.duid)
        self.assertEqual(result.get_option_of_type(IANAOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_ADDRS_AVAIL)
        self.assertEqual(result.get_option_of_type(IAPDOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_PREFIX_AVAIL)

        # Check if the handlers are called correctly
        for method_name in ['pre', 'handle', 'post']:
            method = getattr(self.dummy_handler, method_name)

            self.assertEqual(method.call_count, 1)
            args, kwargs = method.call_args
            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)
            self.assertIsInstance(args[0], TransactionBundle)

        # Check the types and values at various stages
        # In the pre phase there is no response yet
        bundle = self.dummy_handler.pre.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one', 'two',
                                        'pre-setup'})
        self.assertIsNone(bundle.response)
        self.assertIsNone(bundle.outgoing_relay_messages)

        # In the handle phase there is an AdvertiseMessage
        bundle = self.dummy_handler.handle.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one', 'two',
                                        'pre-setup', 'pre-cleanup',
                                        'handle-setup'})
        self.assertIsInstance(bundle.response, AdvertiseMessage)
        self.assertEqual(bundle.outgoing_relay_messages, [])

        # In the post phase there is still an AdvertiseMessage (rapid commit, but no rapid commit rejections)
        bundle = self.dummy_handler.post.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one', 'two',
                                        'pre-setup', 'pre-cleanup',
                                        'handle-setup', 'handle-cleanup',
                                        'post-setup'})
        self.assertIsInstance(bundle.response, AdvertiseMessage)
        self.assertEqual(bundle.outgoing_relay_messages, [])

    def test_very_rapid_solicit_message(self):
        bundle = TransactionBundle(incoming_message=solicit_message,
                                   received_over_multicast=True,
                                   marks=['one'])
        self.very_rapid_message_handler.handle(bundle, StatisticsSet())
        result = bundle.outgoing_message

        self.assertIsInstance(result, ReplyMessage)
        self.assertEqual(result.transaction_id, solicit_message.transaction_id)
        self.assertEqual(result.get_option_of_type(ClientIdOption), solicit_message.get_option_of_type(ClientIdOption))
        self.assertEqual(result.get_option_of_type(ServerIdOption).duid, self.duid)
        self.assertEqual(result.get_option_of_type(IANAOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_ADDRS_AVAIL)
        self.assertEqual(result.get_option_of_type(IAPDOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_PREFIX_AVAIL)

        # Check if the handlers are called correctly
        for method_name in ['pre', 'handle', 'post']:
            method = getattr(self.dummy_handler, method_name)

            self.assertEqual(method.call_count, 1)
            args, kwargs = method.call_args
            self.assertEqual(len(args), 1)
            self.assertEqual(len(kwargs), 0)
            self.assertIsInstance(args[0], TransactionBundle)

        # Check the types and values at various stages
        # In the pre phase there is no response yet
        bundle = self.dummy_handler.pre.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one',
                                        'pre-setup'})
        self.assertIsNone(bundle.response)
        self.assertIsNone(bundle.outgoing_relay_messages)

        # In the handle phase there is an AdvertiseMessage
        bundle = self.dummy_handler.handle.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one',
                                        'pre-setup', 'pre-cleanup',
                                        'handle-setup'})
        self.assertIsInstance(bundle.response, AdvertiseMessage)
        self.assertEqual(bundle.outgoing_relay_messages, [])

        # In the post phase there is a ReplyMessage(rapid commit rejections)
        bundle = self.dummy_handler.post.call_args[0][0]
        self.assertEqual(bundle.request, solicit_message)
        self.assertEqual(bundle.incoming_relay_messages, [])
        self.assertEqual(bundle.marks, {'one',
                                        'pre-setup', 'pre-cleanup',
                                        'handle-setup', 'handle-cleanup',
                                        'post-setup'})
        self.assertIsInstance(bundle.response, ReplyMessage)
        self.assertEqual(bundle.outgoing_relay_messages, [])

    def test_request_message(self):
        bundle = TransactionBundle(incoming_message=request_message,
                                   received_over_multicast=True,
                                   marks=['one'])
        self.message_handler.handle(bundle, StatisticsSet())
        result = bundle.outgoing_message

        self.assertIsInstance(result, ReplyMessage)
        self.assertEqual(result.transaction_id, solicit_message.transaction_id)
        self.assertEqual(result.get_option_of_type(ClientIdOption), solicit_message.get_option_of_type(ClientIdOption))
        self.assertEqual(result.get_option_of_type(ServerIdOption).duid, self.duid)
        self.assertEqual(result.get_option_of_type(IANAOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_ADDRS_AVAIL)
        self.assertEqual(result.get_option_of_type(IAPDOption).get_option_of_type(StatusCodeOption).status_code,
                         STATUS_NO_PREFIX_AVAIL)

    def test_confirm_message(self):
        with self.assertLogs() as cm:
            bundle = TransactionBundle(incoming_message=confirm_message,
                                       received_over_multicast=True,
                                       marks=['one'])
            self.message_handler.handle(bundle, StatisticsSet())
            result = bundle.outgoing_message

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], '^WARNING:.*:No handler confirmed')

        self.assertIsInstance(result, ReplyMessage)
        self.assertEqual(result.transaction_id, request_message.transaction_id)
        self.assertEqual(result.get_option_of_type(ClientIdOption), solicit_message.get_option_of_type(ClientIdOption))
        self.assertEqual(result.get_option_of_type(ServerIdOption).duid, self.duid)
        self.assertEqual(result.get_option_of_type(StatusCodeOption).status_code, STATUS_NOT_ON_LINK)

    def test_empty_confirm_message(self):
        bundle = TransactionBundle(incoming_message=ConfirmMessage(transaction_id=b'abcd'),
                                   received_over_multicast=True,
                                   marks=['one'])
        self.message_handler.handle(bundle, StatisticsSet())
        result = bundle.outgoing_message

        # ConfirmMessage without IANAOption/IATAOption/IAPDOption must be ignored
        self.assertIsNone(result)

    def test_not_implemented_message(self):
        class NotImplementedMessage(ClientServerMessage):
            """
            A non-existent message type to check how we handle unknown messages
            """
            message_type = 255
            from_client_to_server = True

        with self.assertLogs() as cm:
            bundle = TransactionBundle(incoming_message=NotImplementedMessage(transaction_id=b'abcd'),
                                       received_over_multicast=True,
                                       marks=['one'])
            self.message_handler.handle(bundle, StatisticsSet())
            result = bundle.outgoing_message

        self.assertEqual(len(cm.output), 1)
        self.assertRegex(cm.output[0], '^WARNING:.*:Do not know how to reply')

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
