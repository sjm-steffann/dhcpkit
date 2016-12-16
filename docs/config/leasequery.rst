.. _leasequery:

Leasequery
==========

Implement the Leasequery protocol (:rfc:`5007`) and Bulk Leasequery protocol (:rfc:`5460`).


Example
-------

.. code-block:: dhcpkitconf

    <leasequery>
        allow-from 2001:db8::ffff:1
        allow-from 2001:db8:1:2::/64

        sensitive-option sip-servers-domain-name-list
        sensitive-option sip-servers-address-list

        <lq-sqlite /var/lib/dhcpkit/leasequery.sqlite />
    </leasequery>

.. _leasequery_parameters:

Section parameters
------------------

allow-from (multiple allowed)
    Leasequeries are not used for normal operations. They can disclose information about clients on your
    network. Therefore you can specify from which clients to accept leasequeries.

    Not specifying any trusted clients will allow leasequeries from everywhere. This is strongly not
    recommended.

    Also note that this only limits which clients may use the leasequery protocol. Clients that are
    performing bulk leasequeries also need to set up a TCP connection to this server. This has to be
    explicitly allowed in the :ref:`listen-tcp` listener.

    **Example**:

    .. code-block:: dhcpkitconf

        allow-from 2001:db8::ffff:1
        allow-from 2001:db8:beef::/48

sensitive-option (multiple allowed)
    DHCPv6 servers SHOULD be configurable with a list of "sensitive options" that must not be returned to
    the requestor when specified in the OPTION_ORO of the OPTION_LQ_QUERY option in the LEASEQUERY message.
    Any option on this list MUST NOT be returned to a requestor, even if requested by that requestor.

    **Example**:

    .. code-block:: dhcpkitconf

        sensitive-option recursive-name-servers
        sensitive-option 23

Possible sub-section types
--------------------------

:ref:`Leasequery_store <leasequery_store>` (required)
    Configuration sections that define Leasequery stores. Each leasequery section must configure exactly one
    store. Stores perform the storing of lease data at the end of a DHCPv6 request. They also handle the queries
    from Leasequery clients to search in that stored data.

