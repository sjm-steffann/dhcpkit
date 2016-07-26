.. _ipv6-dhcpd:

ipv6-dhcpd(8)
=============
.. program:: ipv6-dhcpd

Synopsis
--------
ipv6-dhcpd [-h] [-v] [-p PIDFILE] config


Description
-----------
This is the executable that runs the DHCP server code. Its functionality depends on the handler modules configured in
the configuration file. These can implement anything from printing incoming packets to providing a fully functional
stateful DHCP server.


Command line options
--------------------
.. option:: config

    is the :doc:`configuration file </config/config_file>`.

.. option:: -h, --help

    show the help message and exit.

.. option:: -v, --verbosity

    increase output verbosity. This option can be provided up to five times to increase the verbosity level. If the
    :mod:`colorlog` package is installed logging will be in colour.

.. option:: -p PIDFILE, --pidfile PIDFILE

    save the server's PID to this file


Security
--------
Because it has to be able to bind to the DHCPv6 server UDP port (547) it has to be started as `root`. The process will
give up `root` privileges after it reads the configuration file and opens the listening sockets.
