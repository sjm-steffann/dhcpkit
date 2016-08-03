.. _map-e:

Map-e
=====

Configure MAP-E mappings to send to a client.


Example
-------

.. code-block:: dhcpkitconf

    <map-e>
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

        br-address 2001:db8::1
        br-address 2001:db8::2
    </map-e>

.. _map-e_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

br-address (required, multiple allowed)
    The IPv6 address of the Border Relay (a.k.a. AFTR) to use for reaching IPv4 sites outside the
    configured mappings.

Possible sub-section types
--------------------------

:ref:`Map-rule <map-rule>` (required, multiple allowed)
    A mapping rule for MAP implementations.

