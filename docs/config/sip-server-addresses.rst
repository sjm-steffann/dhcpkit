.. _sip-server-addresses:

Sip-server-addresses
====================

This sections adds SIP server addresses to the response sent to the client. If there are multiple sections
of this type then they will be combined into one set of servers which is sent to the client.


Example
-------

.. code-block:: dhcpkitconf

    <sip-server-addresses>
        address 2001:db8::1
        address 2001:db8::2
    </sip-server-addresses>

.. _sip-server-addresses_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

address (required, multiple allowed)
    The IPv6 address of a SIP server.

    **Example**: "2001:db8::1"

