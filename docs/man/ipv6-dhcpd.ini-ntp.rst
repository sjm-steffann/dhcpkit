NTP Servers option handler
==========================
This option handler adds an :class:`.NTPServersOption` to replies where appropriate. It contains a list of NTP servers
that the client can use. The servers can be specified as unicast addresses (``server-address``, multicast addresses
(``multicast-address``) and hostnames (``server-fqdn``). Each option only accepts one address or name.

An example configuration for this option:

.. code-block:: ini

    [option NTPServers]
    server-address = 2001:db8::1
    multicast-address-1 = ff12::1:2:3
    multicast-address-2 = ff12::2:3:4
    server-fqdn = ntp.example.com

The numbers at the end are just for distinguishing the options from each other and can be any numerical value. The
values are sent to the client in the order they appear, not according to their numbers.
