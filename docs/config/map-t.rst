.. _map-t:

Map-t
=====

Configure MAP-T mappings to send to a client.


Example
-------

.. code-block:: dhcpkitconf

    <map-t>
        <map-rule>
            ipv6-prefix 2001:db8:f000::/36
            ipv4-prefix 192.0.2.0/24
            contiguous-ports 64
            sharing-ratio 16
            forwarding-mapping yes
        </map-rule>

        <map-rule>
            ipv6-prefix 2001:db8:9500::/40
            ipv4-prefix 198.51.100.0/24
            contiguous-ports 4
            sharing-ratio 256
        </map-rule>

        default-mapping 2001:db8:0:1::/64
    </map-t>

.. _map-t_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

default-mapping (required)
    The /64 prefix to use for reaching IPv4 sites outside the configured mappings.

Possible sub-section types
--------------------------

:ref:`Map-rule <map-rule>` (required, multiple allowed)
    A mapping rule for MAP implementations.

