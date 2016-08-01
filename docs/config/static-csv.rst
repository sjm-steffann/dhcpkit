.. _static-csv:

Static-csv
==========

This section specifies that clients get their address and/or prefix assigned based on the contents of a
CSV file. The filename is given as the name of the section. Relative paths are resolved relative to the
configuration file.

.. _csv-file-structure:

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

:samp:`subscriber-id:{value}`
    where ``value`` is the value of the subscriber-id in hexadecimal notation.

:samp:`subscriber-id-str:{value}`
    where ``value`` is the value of the subscriber-id in ascii notation.

:samp:`linklayer-id:{type}:{value}`
    where ``type`` is a hardware type assigned by the IANA, as described in :rfc:`826` (ethernet has type
    number 1) and ``value`` is the value of the link-layer address in hexadecimal notation.

:samp:`linklayer-id-str:{type}:{value}`
    where ``type`` is a hardware type assigned by the IANA, as described in :rfc:`826` (ethernet has type
    number 1) and ``value`` is the value of the link-layer address in ascii notation.

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


Example
-------

.. code-block:: dhcpkitconf

    <static-csv data/assignments.csv>
        address-preferred-lifetime 1d
        address-valid-lifetime 7d
        prefix-preferred-lifetime 3d
        prefix-valid-lifetime 30d
    </static-csv>

.. _static-csv_parameters:

Section parameters
------------------

address-preferred-lifetime
    The preferred lifetime of assigned addresses. This is the time that the client should use it as the
    source address for new connections. After the preferred lifetime expires the address remains valid but
    becomes deprecated.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "7d"

address-valid-lifetime
    The valid lifetime of assigned addresses. After this lifetime expires the client is no longer allowed
    to use the assigned address.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "30d"

prefix-preferred-lifetime
    The preferred lifetime of assigned prefixes. This is the time that the client router should use as a
    preferred lifetime value when advertising prefixes to its clients.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "7d"

prefix-valid-lifetime
    The valid lifetime of assigned prefixes. This is the time that the client router should use as a
    valid lifetime value when advertising prefixes to its clients.

    The value is specified in seconds. For ease of use these suffixes may be used: 's' (seconds),
    'm' (minutes), 'h' (hours), or 'd' (days).

    **Default**: "30d"

