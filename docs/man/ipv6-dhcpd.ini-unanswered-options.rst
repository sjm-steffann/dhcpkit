Unanswered option handlers
==========================
If no other handler answers to address or prefix requests from a client then these handlers will provide appropriate
answers telling the client that no addresses are available. The :ref:`standard message handler
<standard_message_handler>` will automatically add these option handlers if they are not configured manually.

Option handler ``UnansweredIA`` will provide answers to :class:`.IANAOption` and :class:`.IATAOption`. Option handler
``UnansweredIAPD`` will provide answers to :class:`.IAPDOption`.

The only setting for these handlers is whether they should claim to be authoritative or not. An authoritative handler
will tell the client that tries to renew or rebind its addresses that those addresses are no longer valid and should be
removed. A non-authoritative handler will tell the client that it doesn't have any bindings for those addresses and
allow the client to find another DHCPv6 server that can rebind them. The default setting is to **not** be authoritative.

Example configurations for these options:

.. code-block:: ini

    [option UnansweredIA]
    authoritative = yes

    [option UnansweredIAPD]
    authoritative = no
