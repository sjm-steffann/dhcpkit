.. _lq-sqlite:

Lq-sqlite
=========

This leasequery store will store observed leases seen in DHCPv6 reply messages in the SQLite database whose
name is provided as the name of the section. It implements the query types from both the
Leasequery (:rfc:`5007`) and Bulk Leasequery (:rfc:`5460`) protocol extensions.


Example
-------

.. code-block:: dhcpkitconf

    <lq-sqlite /var/lib/dhcpkit/leasequery.sqlite />

