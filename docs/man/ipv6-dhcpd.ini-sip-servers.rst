SIP Servers Address List option handler
=======================================
This option handler adds a :class:`.SIPServersAddressListOption` to replies where appropriate. It contains a list of SIP
server addresses that the client can use.

An example configuration for this option:

.. code-block:: ini

    [option SIPServersAddressList]
    server-address-1 = 2001:db8::1
    server-address-2 = 2001:db8::2

The numbers at the end are just for distinguishing the options from each other and can be any numerical value. The
addresses are sent to the client in the order they appear, not according to their numbers.

SIP Servers Domain Name List option handler
===========================================
This option handler adds a :class:`.SIPServersDomainNameListOption` to replies where appropriate. It contains a list of
SIP server domain names that the client can use.

An example configuration for this option:

.. code-block:: ini

    [option SIPServersDomainNameList]
    domain-name-1 = example.com
    domain-name-2 = example.net

The numbers at the end are just for distinguishing the options from each other and can be any numerical value. The
domain names are sent to the client in the order they appear, not according to their numbers.
