.. _recursive-name-servers:

Recursive-name-servers
======================

This sections adds recursive name servers to the response sent to the
client. If there are multiple sections of this type then they will be
combined into one set of recursive name servers which is sent to the
client.


Example
-------

.. code-block:: dhcpkitconf

    <recursive-name-servers>
        address 2001:4860:4860::8888
        address 2001:4860:4860::8844
    </recursive-name-servers>

.. _recursive-name-servers_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

address (required, multiple allowed)
    The IPv6 address of a recursive name server.

    **Example**: "2001:db8:1::53"

