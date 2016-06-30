.. _duid-en:

Duid-en
=======

A DUID based on an enterprise-number and an opaque identifier.


Example
-------

.. code-block:: dhcpkitconf

    <duid-en>
        enterprise-number 40208
        identifier 12:34:56:78:90:ab:cd:ef
    </duid-en>

.. _duid-en_parameters:

Section parameters
------------------

enterprise-number (required)
    This must be a Private Enterprise Number as maintained by IANA.
    See http://www.iana.org/assignments/enterprise-numbers.

identifier (required)
    This is a unique identifier assigned by the specified enterprise. The value must be provided as a
    hexadecimal string. Each octet may be separated with colons, but this is not required.

    **Example**: "12:34:56:78:90:ab:cd:ef:ca:fe:be:ef"

