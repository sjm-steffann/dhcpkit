.. _copy-remote-id:

Copy-remote-id
==============

A DHCPv6 server is not required to copy the remote-id option from a request to the response and echo it back
to the relay. If you want to echo it back then include this handler to do so.


Example
-------

.. code-block:: dhcpkitconf

    <copy-remote-id/>

