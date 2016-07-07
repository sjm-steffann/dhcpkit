.. _server-unicast:

Server-unicast
==============

This handler tells clients that they may contact it using unicast.


Example
-------

.. code-block:: dhcpkitconf

    <server-unicast>
        address 2001:db8::1:2:3
    </server-unicast>

.. _server-unicast_parameters:

Section parameters
------------------

address (required)
    The IPv6 unicast address that the client may send requests to

