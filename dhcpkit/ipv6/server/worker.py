"""
Worker process for handling requests using multiprocessing.
"""
import logging
import logging.handlers
import re
import signal
from multiprocessing import Queue, current_process

from typing import Optional

from dhcpkit.ipv6 import SERVER_PORT, CLIENT_PORT
from dhcpkit.ipv6.messages import RelayForwardMessage, Message, RelayReplyMessage
from dhcpkit.ipv6.options import InterfaceIdOption, RelayMessageOption
from dhcpkit.ipv6.server.listeners import IncomingPacketBundle, OutgoingPacketBundle
from dhcpkit.ipv6.server.message_handler import MessageHandler

# These globals will be set by setup_worker()
from dhcpkit.ipv6.server.queue_logger import WorkerQueueHandler

logger = None
""":type: logging.Logger"""

logging_handler = None
""":type: WorkerQueueHandler"""

current_message_handler = None
""":type: MessageHandler"""


def setup_worker(message_handler: MessageHandler, logging_queue: Queue, lowest_log_level: int):
    """
    This function will be called after a new worker process has been created. Its purpose is to set the global
    variables in this specific worker process so that they can be reused across multiple requests. Otherwise we would
    have to pickle them each and every time, and because they are static that would be a waste.

    :param message_handler: The message handler for the incoming requests
    :param logging_queue: The queue where we can deposit log messages so the main process can log them
    :param lowest_log_level: The lowest log level that is going to be handled by the main process
    """
    # Let's shorten the process name a bit by removing everything except the "Worker-x" bit at the end
    this_process = current_process()
    this_process.name = re.sub(r'^.*(Worker-\d+)$', r'\1', this_process.name)

    # Ignore normal signal handling
    signal.signal(signal.SIGINT, lambda signum, frame: None)
    signal.signal(signal.SIGTERM, lambda signum, frame: None)
    signal.signal(signal.SIGHUP, lambda signum, frame: None)

    # Save the logger, don't let it filter, send everything to the queue
    global logger
    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)

    global logging_handler
    logging_handler = WorkerQueueHandler(logging_queue)
    logging_handler.setLevel(lowest_log_level)
    logger.addHandler(logging_handler)

    # Save the message handler
    global current_message_handler
    current_message_handler = message_handler

    # Run the per-process startup code for the message handler and its children
    message_handler.worker_init()


def parse_incoming_request(incoming_packet: IncomingPacketBundle) -> RelayForwardMessage:
    """
    Parse the incoming packet and add a RelayServerMessage around it containing the meta-data received from the
    listener.

    :param incoming_packet: The received packet
    :return: The parsed message
    """
    length, incoming_message = Message.parse(incoming_packet.data)

    # Determine the next hop count and construct useful log messages
    if isinstance(incoming_message, RelayForwardMessage):
        next_hop_count = incoming_message.hop_count + 1
    else:
        next_hop_count = 0

    # Pretend to be an internal relay and wrap the message like a relay would
    return RelayForwardMessage(hop_count=next_hop_count,
                               link_address=incoming_packet.link_address,
                               peer_address=incoming_packet.sender,
                               options=[
                                   InterfaceIdOption(interface_id=incoming_packet.interface_id),
                                   RelayMessageOption(relayed_message=incoming_message)
                               ])


def generate_outgoing_response(outgoing_message: Message,
                               incoming_packet: IncomingPacketBundle = None) -> OutgoingPacketBundle:
    """
    generate the outgoing packet and check the RelayServerMessage around it.

    :param outgoing_message: The reply message
    :param incoming_packet: The original received packet, only used to sanity-check the reply
    :return: The parsed message
    """
    # Verify that the outer relay message makes sense
    if not isinstance(outgoing_message, RelayReplyMessage):
        raise ValueError("The reply has to be wrapped in a RelayReplyMessage")

    if incoming_packet is not None:
        # Verify the contents of the outgoing message
        if outgoing_message.link_address != incoming_packet.link_address:
            raise ValueError("The relay-reply link-address does not match the relay-forward link-address")

        interface_id_option = outgoing_message.get_option_of_type(InterfaceIdOption)
        if interface_id_option and interface_id_option.interface_id != incoming_packet.interface_id:
            # If there is an interface-id option its contents have to match
            raise ValueError("The interface-id in the reply does not match the interface-id of the request")

    reply = outgoing_message.relayed_message
    if not reply:
        raise ValueError("The RelayReplyMessage does not contain a message")

    # Down to network addresses and bytes
    port = isinstance(reply, RelayReplyMessage) and SERVER_PORT or CLIENT_PORT
    destination = outgoing_message.peer_address
    data = reply.save()

    return OutgoingPacketBundle(message_id=incoming_packet.message_id, data=data, destination=destination, port=port)


def handle_message(incoming_packet: IncomingPacketBundle) -> Optional[OutgoingPacketBundle]:
    """
    Handle a single incoming request. This is supposed to be called in a separate worker thread that has been
    initialised with setup_worker().

    :param incoming_packet: The raw incoming request
    :returns: The packet to reply with and the destination
    """
    # Set the log_id to make it easier to correlate log messages
    logging_handler.log_id = incoming_packet.message_id

    # Instead of having multiple try/except blocks just for better error messages we have one and customise
    # the messages by looking at the phase variable to describe where things went wrong.
    phase = 'parsing request'

    try:
        # Parse the packet
        incoming_message = parse_incoming_request(incoming_packet)

        phase = 'handling request'
        outgoing_message = current_message_handler.handle(incoming_message, incoming_packet.received_over_multicast,
                                                          incoming_packet.marks)

        if outgoing_message:
            phase = 'generating response'
            return generate_outgoing_response(outgoing_message, incoming_packet)

    except Exception as e:
        logger.error("Error while {}: {}".format(phase, e))

    finally:
        # Always reset the log_id when leaving
        logging_handler.log_id = None
