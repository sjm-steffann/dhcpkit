"""
Functions to extract a key from a transaction bundle
"""
import codecs

from dhcpkit.ipv6.extensions.linklayer_id import LinkLayerIdOption
from dhcpkit.ipv6.extensions.remote_id import RemoteIdOption
from dhcpkit.ipv6.extensions.subscriber_id import SubscriberIdOption
from dhcpkit.ipv6.options import ClientIdOption, InterfaceIdOption
from dhcpkit.ipv6.server.transaction_bundle import TransactionBundle


def duid_key(bundle: TransactionBundle) -> str:
    """
    Get the DUID from the request in the transaction bundle

    :param bundle: The transaction bundle
    :return: The DUID in hex notation
    """
    duid = bundle.request.get_option_of_type(ClientIdOption).duid
    return 'duid:{}'.format(
        codecs.encode(duid.save(), 'hex').decode('ascii')
    )


def interface_id_key(bundle: TransactionBundle) -> str:
    """
    Get the Interface-ID from the request in the transaction bundle, with a fallback
    to the DUID if no Interface-ID is found.

    :param bundle: The transaction bundle
    :return: The Interface-ID (or DUID) in hex notation
    """
    interface_id_option = bundle.incoming_relay_messages[0].get_option_of_type(InterfaceIdOption)
    if interface_id_option:
        return 'interface-id:{}'.format(
            codecs.encode(interface_id_option.interface_id, 'hex').decode('ascii')
        )
    else:
        return duid_key(bundle)


def remote_id_key(bundle: TransactionBundle) -> str:
    """
    Get the Remote-ID from the request in the transaction bundle, with a fallback
    to the DUID if no Remote-ID is found.

    :param bundle: The transaction bundle
    :return: The Remote-ID (or DUID) in hex notation
    """
    remote_id_option = bundle.incoming_relay_messages[0].get_option_of_type(RemoteIdOption)
    if remote_id_option:
        return 'remote-id:{}:{}'.format(
            remote_id_option.enterprise_number,
            codecs.encode(remote_id_option.remote_id, 'hex').decode('ascii')
        )
    else:
        return duid_key(bundle)


def subscriber_id_key(bundle: TransactionBundle) -> str:
    """
    Get the Subscriber-ID from the request in the transaction bundle, with a fallback
    to the DUID if no Subscriber-ID is found.

    :param bundle: The transaction bundle
    :return: The Subscriber-ID (or DUID) in hex notation
    """
    subscriber_id_option = bundle.incoming_relay_messages[0].get_option_of_type(SubscriberIdOption)
    if subscriber_id_option:
        return 'subscriber-id:{}'.format(
            codecs.encode(subscriber_id_option.subscriber_id, 'hex').decode('ascii')
        )
    else:
        return duid_key(bundle)


def linklayer_id_key(bundle: TransactionBundle) -> str:
    """
    Get the LinkLayer-ID from the request in the transaction bundle, with a fallback
    to the DUID if no LinkLayer-ID is found.

    :param bundle: The transaction bundle
    :return: The LinkLayer-ID (or DUID) in hex notation
    """
    linklayer_id_option = bundle.incoming_relay_messages[0].get_option_of_type(LinkLayerIdOption)
    if linklayer_id_option:
        return 'linklayer-id:{}:{}'.format(
            linklayer_id_option.link_layer_type,
            codecs.encode(linklayer_id_option.link_layer_address, 'hex').decode('ascii')
        )
    else:
        return duid_key(bundle)


key_function_map = {
    'duid': duid_key,
    'interface-id': interface_id_key,
    'remote-id': remote_id_key,
    'subscriber-id': subscriber_id_key,
    'linklayer-id': linklayer_id_key,
}
