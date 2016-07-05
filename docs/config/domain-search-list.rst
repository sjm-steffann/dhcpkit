.. _domain-search-list:

Domain-search-list
==================

This sections adds domain names to the domain search list sent to the
client. If there are multiple sections of this type then they will be
combined into one set of domain names which is sent to the client.


Example
-------

.. code-block:: dhcpkitconf

    <domain-search-list>
        domain-name example.com
        domain-name example.net
        domain-name example.org
    </domain-search-list>

.. _domain-search-list_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

domain-name (required, multiple allowed)
    The domain name to add to the search list.

    **Example**: "example.com"

