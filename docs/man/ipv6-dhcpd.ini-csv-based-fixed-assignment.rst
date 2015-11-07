CSV based Fixed Assignment option handler
=========================================
This option handler can give fixed assignments to clients based on
the :attr:`DUID of the client <.ClientIdOption.duid>`, the :attr:`Interface-ID <.InterfaceIdOption.interface_id>`
provided by the DHCPv6 relay closest to the client or the :attr:`Enterprise number <.RemoteIdOption.enterprise_number>`
and :attr:`Remote-ID <.RemoteIdOption.remote_id>` provided by the DHCPv6 relay closest to the client.

This option can occur multiple times, once for each client subnet. The subnet prefix is given after the name op the
option handler. If the server should treat multiple prefixes as equivalent then those can be specified with the
``additional-prefixes`` option. The filename of the CSV file containing the assignments is specified with the
``assignments-file`` option. The preferred and valid lifetimes for addresses and prefixes can be specified as well. The
default values are shown in the example below.

An example configuration for this option:

.. code-block:: ini

    [option CSVBasedFixedAssignment 2001:db8:0:1::/64]
    additional-prefixes = 2001:db8:0:2::/64
    assignments-file = assignments.csv
    address-preferred-lifetime = 3600
    address-valid-lifetime = 7200
    prefix-preferred-lifetime = 43200
    prefix-valid-lifetime = 86400

The filename can be an absolute pathname or a filename relative to the configuration file's location. The contents of
the CSV file must contain at least three columns: ``id``, ``address`` and ``prefix``. All other columns are ignored.
The ``address`` and ``prefix`` columns may have empty values. The ``id`` column must contain a value in one of these
formats:

:samp:`duid:{hex-value}`
    where ``hex-value`` is a hexadecimal string containing in the same format as the :ref:`server DUID <server_duid>`
    value.

:samp:`interface-id:{value}`
    where ``value`` is the value of the interface-id in hexadecimal notation.

:samp:`interface-id-str:{value}`
    where ``value`` is the value of the interface-id in ascii notation.

:samp:`remote-id:{enterprise-number}:{value}`
    where ``enterprise-number`` is an `enterprise number <http://www.iana.org/assignments/enterprise-numbers>`_ as
    registered with IANA and ``value`` is the value of the remote-id in hexadecimal notation.

:samp:`remote-id-str:{enterprise-number}:{value}`
    where ``enterprise-number`` is an `enterprise number <http://www.iana.org/assignments/enterprise-numbers>`_ as
    registered with IANA and ``value`` is the value of the remote-id in ascii notation.

Examples of the different formats recognised by the CSV parser::

        id,address,prefix
        duid:000100011d1d6071002436ef1d89,2001:db8:0:1::2:1,2001:db8:0201::/48
        interface-id:4661322f31,2001:db8:0:1::2:2,2001:db8:0202::/48
        interface-id-str:Fa2/2,2001:db8:0:1::2:3,2001:db8:0203::/48
        remote-id:9:020023000001000a0003000100211c7d486e,2001:db8:0:1::2:4,2001:db8:0204::/48
        remote-id-str:40208:SomeRemoteIdentifier,2001:db8:0:1::2:5,2001:db8:0205::/48

