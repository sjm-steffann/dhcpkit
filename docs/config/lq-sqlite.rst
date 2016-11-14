.. _lq-sqlite:

Lq-sqlite
=========

This leasequery store will store observed leases seen in DHCPv6 reply messages in the SQLite database whose
name is provided as the name of the section. It implements the query types from both the
:rfc:`Leasequery <5007>` and :rfc:`Bulk Leasequery <5460>` protocol extensions.


Example
-------

.. code-block:: dhcpkitconf

    <lq-sqlite /var/lib/dhcpkit/leasequery.sqlite />

