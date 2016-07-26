.. _ipv6-dhcp-build-sqlite:

ipv6-dhcp-build-sqlite(1)
=========================
.. program:: ipv6-dhcp-build-sqlite

Synopsis
--------
ipv6-dhcp-build-sqlite [-h] [-f] [-v] source destination


Description
-----------
This utility converts a :ref:`CSV file with assignments <csv-file-structure>` to a SQLite database for use with the
:ref:`static-sqlite` handler.


Command line options
--------------------
.. option:: source

    is the source CSV file

.. option:: destination

    is the destination SQLite file

.. option:: -h, --help

    show the help message and exit.

.. option:: -f, --force

    force removing old entries, even if that means deleting more than 30% of the contents of the database

.. option:: -v, --verbosity

    increase output verbosity. This option can be provided up to five times to increase the verbosity level. If the
    :mod:`colorlog` package is installed logging will be in colour.


Concurrency
-----------
This utility implements some functionality to make it possible to run it against a SQLite database that is being
concurrently used by a DHCPv6 server. It will release the write lock on the database every so often to allow the server
to continue its processing of requests.

While updating the database this tool will check to see if another instance is writing newer entries to the same
database. If this is detected it will abort to let the other instance finish its work.


Safety
------
To prevent the database being destroyed because of an invalid input file this tool compares the size of the number of
entries read from the CSV file with the size of the database. If more than 30% of the database would be deleted because
the corresponding entries dave disappeared from the CSV file the delete action is aborted and old entries are left in
the database. Provide the :option:`--force` option to force removal of those entries.
