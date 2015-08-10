SNTP Servers option handler
===========================
This option handler adds a :class:`.SNTPServersOption` to replies where appropriate. It contains a list of SNTP servers
that the client can use.

An example configuration for this option:

.. code-block:: ini

    [option SNTPServers]
    server-address-1 = 2001:db8::1
    server-address-2 = 2001:db8::2

The numbers at the end are just for distinguishing the options from each other and can be any numerical value. The
addresses are sent to the client in the order they appear, not according to their numbers.
