ipv6-dhcpd(8)
=============
.. program:: ipv6-dhcpd

Synopsis
--------
ipv6-dhcpd [-h] [-C] [-v] config


Description
-----------
This is the executable that runs the DHCP server code. Its functionality depends on the handler modules configured in
the configuration file. These can implement anything from printing incoming packets to providing a fully functional
stateful DHCP server.


Command line options
--------------------
.. option:: config

    is the configuration file as described in :doc:`ipv6-dhcpd.ini`.

.. option:: -h, --help

    show the help message and exit.

.. option:: -C, --show-config

    show the active configuration after parsing the configuration file.

.. option:: -v, --verbosity

    increase output verbosity. This option can be provided up to three times to increase the verbosity level. If the
    :mod:`colorlog` package is installed logging will be in colour.


Security
--------
Because it has to be able to bind to the DHCPv6 server UDP port (547) it has to be started as `root`. The process will
give up `root` privileges after it reads the configuration file and opens the listening sockets.


See also
--------
:manpage:`ipv6-dhcpd.ini(5)`
