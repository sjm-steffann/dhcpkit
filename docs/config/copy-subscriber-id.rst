.. _copy-subscriber-id:

Copy-subscriber-id
==================

A DHCPv6 server is not required to copy the subscriber-id option from a request to the response and echo it
back to the relay. If you want to echo it back then include this handler to do so.


Example
-------

.. code-block:: dhcpkitconf

    <copy-subscriber-id/>

