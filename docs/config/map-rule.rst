.. _map-rule:

Map-rule
========

A mapping rule for MAP implementations.


Example
-------

.. code-block:: dhcpkitconf

    <map-rule>
        ipv6-prefix 2001:db8:f000::/36
        ipv4-prefix 192.0.2.0/24
        contiguous-ports 64
        sharing-ratio 16
        forwarding-mapping yes
    </map-rule>

.. _map-rule_parameters:

Section parameters
------------------

ipv6-prefix (required)
    The IPv6 prefix containing MAP clients.

ipv4-prefix (required)
    The IPv4 prefix that the MAP clients will share.

contiguous-ports (required)
    The number of contiguous ports. This value must be a power of 2. It determines the number of bits after
    the PSID.

sharing-ratio (required)
    The number of customers sharing one IPv4 address. This value must be a power of 2. It determines the
    length of the PSID.

forwarding-mapping
    Whether this rule is a Forwarding Mapping Rule (FMR) or a Basic Mapping Rule (BMR).

    **Default**: "no"

