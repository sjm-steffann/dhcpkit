.. _sntp-servers:

Sntp-servers
============

This sections adds SNTP servers to the response sent to the client. If there are multiple sections of this
type then they will be combined into one set of SNTP servers which is sent to the client.


Example
-------

.. code-block:: dhcpkitconf

    <sntp-servers>
        address 2610:20:6F15:15::27
    </sntp-servers>

.. _sntp-servers_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

address (required, multiple allowed)
    IPv6 address of an SNTP server

    **Example**: "2610:20:6F15:15::27"

