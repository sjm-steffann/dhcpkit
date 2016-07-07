.. _ntp-servers:

Ntp-servers
===========

This sections adds NTP servers to the response sent to the client. If there are multiple sections of this
type then they will be combined into one set of NTP servers which is sent to the client.


Example
-------

.. code-block:: dhcpkitconf

    <ntp-servers>
        server-fqdn time-d.nist.gov
        server-address 2610:20:6F15:15::27
        multicast-address ff08::101
    </ntp-servers>

.. _ntp-servers_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

<multiple> (required, multiple allowed)
    The key is the type of NTP server reference and the data is the corresponding reference. Built-in
    NTP server reference types are 'server-fqdn', 'server-address' and 'multicast-address'.

    **Example**: "server-fqdn time-d.nist.gov"

