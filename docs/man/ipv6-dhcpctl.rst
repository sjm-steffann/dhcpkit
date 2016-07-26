.. _ipv6-dhcpctl:

ipv6-dhcpctl(8)
===============
.. program:: ipv6-dhcpctl

Synopsis
--------
ipv6-dhcpctl [-h] [-v] [-c FILENAME] command


Description
-----------
A remote control utility that allows you to send commands to the DHCPv6 server.


Command line options
--------------------
.. option:: command

    is the command to send to the server. Use the `help` command to see what commands are available from your server.

.. option:: -h, --help

    show the help message and exit.

.. option:: -v, --verbosity

    increase output verbosity. This option can be provided up to five times to increase the verbosity level. If the
    :mod:`colorlog` package is installed logging will be in colour.

.. option:: -c FILENAME, --control-socket FILENAME

    location of domain socket for server control. The default socket is /var/run/ipv6-dhcpd.sock which is also the
    default location where the server will create its control socket.
