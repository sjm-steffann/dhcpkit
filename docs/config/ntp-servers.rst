.. _ntp-servers:

Ntp-servers
===========

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
    </static-csv>

.. _ntp-servers_parameters:

Section parameters
------------------

+ (required, multiple allowed)


