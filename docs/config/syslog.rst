.. _syslog:

Syslog
======

Log to local syslog. The name of the section is the destination, which can be a ``hostname:port`` or a unix
socket file name. Relative names are resolved relative to the directory containing the configuration file.


Example
-------

.. code-block:: dhcpkitconf

    # This will try to auto-detect the syslog socket using the default level
    <syslog />

    # This logs explicitly to the specified socket using a non-default facility
    <syslog /var/run/syslog>
        facility local3
        level info
    </syslog>

    # This logs explicitly to the specified socket using a non-default protocol
    <syslog collector.example.com:514>
        facility local1
        protocol tcp
    </syslog>

.. _syslog_parameters:

Section parameters
------------------

level
    The log level. Only log messages with a priority of this level or higher are logged to this output.
    Possible values are:

    "critical"
        Log critical errors that prevent the server from working

    "error"
        Log errors that occur

    "warning"
        Log warning messages that might indicate a problem

    "info"
        Log informational messages

    "debug"
        Log messages that are usually only useful when debugging issues

    "debug-packets"
        Log the sending and receiving of packets

    "debug-handling"
        Log everything about how a request is handled

    **Default**: "warning"

facility
    Use the specified log facility. The available facilities are system-dependent but usually include
    "daemon", "local0" to "local7", "auth", "user" and "syslog".

    **Default**: "daemon"

protocol
    Use a datagram ("dgram" or "udp") or stream ("stream" or "tcp") connection

    **Default**: "dgram"

