.. _console:

Console
=======

Log to console.


Example
-------

.. code-block:: dhcpkitconf

    <console>
        level debug-handling
        color yes
    </console>

.. _console_parameters:

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

color
    Whether to show log entries in colour

    **Default**: auto-detect colour support

