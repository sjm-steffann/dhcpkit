.. _duid-llt:

Duid-llt
========

A DUID based on a link-layer address and a timestamp.


Example
-------

.. code-block:: dhcpkitconf

    <duid-llt>
        hardware-type 1
        link-layer-address 002436ef1d89
        timestamp 2016-12-31T23:59:59Z
    </duid-llt>

    <duid-llt server-id>
        hardware-type 1
        link-layer-address 00:24:36:ef:1d:89
        timestamp 2016-12-31T23:59:59Z
    </duid-llt>

.. _duid-llt_parameters:

Section parameters
------------------

hardware-type (required)
    The hardware type must be a valid hardware type assigned by the IANA, as described in :rfc:`826`.
    Ethernet has type number 1.

link-layer-address (required)
    The link-layer address must be provided as a hexadecimal string. Each octet may be separated with
    colons, but this is not required.

    **Example**: "00:24:36:ef:1d:89"

timestamp (required)
    The timestamp to include in the address. It must be provided in the ISO-8601 compatible
    format "%Y-%m-%dT%H:%M:%SZ".

    **Example**: "2016-12-31T23:59:59Z"

