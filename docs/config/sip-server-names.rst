.. _sip-server-names:

Sip-server-names
================

This sections adds SIP server domain names to the response sent to the client. If there are multiple
sections of this type then they will be combined into one set of domain names which is sent to the client.

The option MAY contain multiple domain names, but these SHOULD refer to different NAPTR records, rather
than different A records.


Example
-------

.. code-block:: dhcpkitconf

    <sip-server-names>
        domain-name example.org
    </sip-server-names>

.. _sip-server-names_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

domain-name (required, multiple allowed)
    The domain name to add to the list. This should refer to a NAPTR record.

    **Example**: "example.com"

