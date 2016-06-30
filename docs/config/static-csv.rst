.. _static-csv:

Static-csv
==========

This section specifies that clients get their address and/or prefix assigned based on the contents of a
CSV file. The filename is given as the name of the section, and is relative to the configuration file.

The CSV file must have a heading defining the field names, and the fields ``id``, ``address`` and
``prefix`` must be present. All other columns are ignored.

The id can refer to the :attr:`DUID of the client <.ClientIdOption.duid>`,
the :attr:`Interface-ID <.InterfaceIdOption.interface_id>` provided by the DHCPv6 relay closest to the
client or the :attr:`Remote-ID <.RemoteIdOption.remote_id>` provided by the DHCPv6 relay closest to the
client. It is specified in one of these formats:

:samp:`duid:{hex-value}`
    where ``hex-value`` is a hexadecimal string containing the DUID of the client.

:samp:`interface-id:{value}`
    where ``value`` is the value of the interface-id in hexadecimal notation.

:samp:`interface-id-str:{value}`
    where ``value`` is the value of the interface-id in ascii notation.

:samp:`remote-id:{enterprise-number}:{value}`
    where ``enterprise-number`` is an
    `enterprise number <http://www.iana.org/assignments/enterprise-numbers>`_ as
    registered with IANA and ``value`` is the value of the remote-id in hexadecimal notation.

:samp:`remote-id-str:{enterprise-number}:{value}`
    where ``enterprise-number`` is an
    `enterprise number <http://www.iana.org/assignments/enterprise-numbers>`_ as
    registered with IANA and ``value`` is the value of the remote-id in ascii notation.

The address column can contain an IPv6 address and the prefix column can contain an IPv6 prefix in
CIDR notation. Both the address and prefix columns may have empty values.

For example:

.. code-block:: none

    id,address,prefix
    duid:000100011d1d6071002436ef1d89,,2001:db8:0201::/48
    interface-id:4661322f31,2001:db8:0:1::2:2,2001:db8:0202::/48
    interface-id-str:Fa2/2,2001:db8:0:1::2:3,
    remote-id:9:020023000001000a0003000100211c7d486e,2001:db8:0:1::2:4,2001:db8:0204::/48
    remote-id-str:40208:SomeRemoteIdentifier,2001:db8:0:1::2:5,2001:db8:0205::/48

.. _static-csv_parameters:

Section parameters
------------------

address-preferred-lifetime


    **Default**: "30m"

address-valid-lifetime


    **Default**: "60m"

prefix-preferred-lifetime


    **Default**: "12h"

prefix-valid-lifetime


    **Default**: "24h"

