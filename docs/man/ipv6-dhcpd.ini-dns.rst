.. _RecursiveNameServersOptionHandler_configuration:

Recursive Name Servers option handler
=====================================
This option handler adds a :class:`RecursiveNameServersOption <dhcpkit.ipv6.extensions.dns.RecursiveNameServersOption>`
to replies where appropriate. It contains a list of DNS resolvers that the client can use.

An example configuration for this option:

.. code-block:: ini

    [option RecursiveNameServers]
    server-address-1 = 2001:db8::8888
    server-address-2 = 2001:db8::8844

The numbers at the end are just for distinguishing the options from each other and can be any numerical value. The
addresses are sent to the client in the order they appear, not according to their numbers.

Domain Search List option handler
=================================
This option handler adds a :class:`.DomainSearchListOption` to replies where appropriate. It contains a list of DNS
domain names that the client can use when resolving unqualified names.

An example configuration for this option:

.. code-block:: ini

    [option DomainSearchList]
    domain-name-1 = example.com
    domain-name-2 = example.org

The numbers at the end are just for distinguishing the options from each other and can be any numerical value. The
domain names are sent to the client in the order they appear, not according to their numbers.
