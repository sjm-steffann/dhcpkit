.. _listen-tcp:

Listen-tcp
==========

This listener listens for TCP connections on the unicast address specified as the name of the section. This
is for BulkLeasequery support, but as an extension the server will also answer other types of messages.


Example
-------

.. code-block:: dhcpkitconf

    <listen-tcp>
        address 2001:db8::1:2

        allow-from 2001:db8::ffff:1
        allow-from 2001:db8:1:2::/64
    </listen-tcp>

.. _listen-tcp_parameters:

Section parameters
------------------

mark (multiple allowed)
    Every incoming request can be marked with different tags. That way you can handle messages differently
    based on i.e. which listener they came in on. Every listener can set one or more marks. Also see the
    :ref:`marked-with` filter.

    **Default**: "unmarked"

address (required)
    Accept TCP connections on the specified address.

    **Example**: "2001:db8::ffff:1"

max-connections
    Limit the number of accepted TCP connections. Servers MUST be able to limit the number of currently
    accepted and active connections.

    **Example**: "20"

    **Default**: "10"

allow-from (multiple allowed)
    TCP connections are not used for normal operations. They are used by Leasequery clients and other
    trusted clients for management purposes. Therefore you can specify from which clients to accept
    connections.

    Not specifying any trusted clients will allow connections from everywhere. This is strongly not
    recommended.

    Also note that this only limits which clients may set up a TCP connection to this server. The leasequery
    section contains a list of clients which are allowed to use the leasequery protocol. Clients that are
    allowed to connect over TCP should probably also be allowed to perform leasequeries.

    **Example**:

    .. code-block:: dhcpkitconf

        allow-from 2001:db8::ffff:1
        allow-from 2001:db8:beef::/48

