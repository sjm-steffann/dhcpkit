Configuration file format
=========================

This describes the configuration file for DHCPKit. The syntax of this file is loosely based on the Apache
configuration style. It is implemented using `ZConfig <https://pypi.python.org/pypi/ZConfig>`_.

The configuration file consists of :ref:`basic server settings <schema_parameters>`, :ref:`listeners` that
receive messages from the network and some :ref:`handlers` that process the request and generate the response
(possibly surrounded by :ref:`filters` that determine which handlers get applies to which request).


Example
-------

.. code-block:: dhcpkitconf

    # Logging to console and syslog
    <logging>
        <console>
            level debug-packets
        </console>
        <syslog>
            level info
        </syslog>
    </logging>

    # Run as user 'demo' with group 'nogroup'
    user demo
    group nogroup

    # Listen to this unicast address (to receive messages from a relay)
    <listen-unicast 2001:db8::1>
        interface en0
    </listen-unicast>

    # Handlers that are only applied to this /48
    <subnet 2001:db8:1::/48>
        # Ignore requests from this /64
        <subnet 2001:db8:1:2::/64>
            <ignore-request/>
        </subnet-group>

        # Everybody else: assign static address/prefix from this CSV
        <static-csv static.csv />
    </subnet>

.. _schema_parameters:

Configuration options
---------------------

user
    The user name the server should run as.

    **Default**: "nobody"

group
    The group name the server should run as.

    **Default**: The primary group of the user.

pid-file
    Save the PID of the main process to this file.

    **Example**: "/var/run/ipv6-dhcpd.pid"

    **Default**: "/var/run/ipv6-dhcpd.pid"

control-socket
    Create a domain socket in this location to control the server.

    **Example**: "/var/run/ipv6-dhcpd.sock"

    **Default**: "/var/run/ipv6-dhcpd.sock"

control-socket-user
    User that owns the control-socket.

control-socket-group
    Group that owns the control-socket.

workers
    The number of worker processes that will be started.

    **Default**: The number of CPUs detected in your system.

allow-rapid-commit
    Whether to allow DHCPv6 rapid commit if the client requests it.

    **Default**: "no"

rapid-commit-rejections
    Whether to allow DHCPv6 rapid commit for responses that reject a request.

    **Default**: "no"

server-id (section of type :ref:`duid`)
    The DUID to use as the server-identifier.

    **Example**:

    .. code-block:: dhcpkitconf

        <duid-ll server-id>
            hardware-type 1
            link-layer-address 00:24:36:ef:1d:89
        </duid-ll>

exception-window
    The length of the exceptions window.

    **Default**: "10.0"

max-exceptions
    The number of exceptions that can occur in the exception window before the server stops itself. This
    prevents the server from spinning in circles when something unexpected goes wrong.

    **Default**: "5"

Possible sub-section types
--------------------------

:ref:`Logging <logging>`
    This section contains the logging configuration. It contains a list of log-handlers that specify where to
    send the log entries.

:ref:`Statistics <statistics>`
    By default the DHCPv6 server only keeps global statistics. Provide categories to collect statistics more
    granularly.

:ref:`Listeners <listeners>` (multiple allowed)
    Configuration sections that define listeners. These are usually the network interfaces that a DHCPv6
    server listens on, like the well-known multicast address on an interface, or a unicast address where a
    DHCPv6 relay can send its requests to.

:ref:`Filters <filters>` (multiple allowed)
    Configuration sections that specify filters. A filter limits which handlers get applied to which messages.
    Everything inside a filter gets ignored if the filter condition doesn't match. That way you can configure
    the server to only apply certain handlers to certain messages, for example to return different information
    options to different clients.

:ref:`Handlers <handlers>` (multiple allowed)
    Configuration sections that specify a handler. Handlers process requests, build the response etc.
    Some of them add information options to the response, others look up the client in a CSV file
    and assign addresses and prefixes, and others can abort the processing and tell the server not to
    answer at all.

    You can make the server do whatever you want by configuring the appropriate handlers.

