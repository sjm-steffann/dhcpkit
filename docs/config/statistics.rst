.. _statistics:

Statistics
==========

By default the DHCPv6 server only keeps global statistics. Provide categories to collect statistics more
granularly.


Example
-------

.. code-block:: dhcpkitconf

    <statistics>
        interface eth0
        subnet 2001:db8:0:1::/64
        subnet 2001:db8:0:2::/64
        relay 2001:db8:1:2::3
    </statistics>

.. _statistics_parameters:

Section parameters
------------------

interface (multiple allowed)
    Collect statistics per server interface

    **Example**: "interface eth0"

subnet (multiple allowed)
    Collect statistics per client subnet

    **Example**: "subnet 2001:db8::/64"

relay (multiple allowed)
    Collect statistics per relay

    **Example**: "relay 2001:db8::1:2"

