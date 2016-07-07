.. _listen-interface:

Listen-interface
================

This listener listens to the DHCPv6 server multicast address on the interface specified as the name of
this section. This is useful to listen for clients on a directly connected LAN.


Example
-------

.. code-block:: dhcpkitconf

    <listen-interface eth0>
        listen-to-self yes
        reply-from fe80::1
        link-address 2001:db8::1
    </listen-interface>

.. _listen-interface_parameters:

Section parameters
------------------

mark (multiple allowed)
    Every incoming request can be marked with different tags. That way you can handle messages differently
    based on i.e. which listener they came in on. Every listener can set one or more marks. Also see the
    :ref:`marked-with` filter.

    **Default**: "unmarked"

listen-to-self
    Usually the server doesn't listen to requests coming from the local host. If you want the server to
    assign addresses to itself (also useful when debugging) then enable this.

    **Default**: "no"

reply-from
    The link-local address to send replies from

    **Default**: The first link-local address found on the interface

link-address
    A global unicast address used to identify the link to filters and handlers.
    It doesn't even need to exist.

    **Default**: The first global unicast address found on the interface, or ``::`` otherwise

