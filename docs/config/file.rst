.. _file:

File
====

Log to a file. The name of the section is the filename of the log file.


Example
-------

.. code-block:: dhcpkitconf

    <file /var/log/dhcpkit/dhcpd.log>
        rotate daily
        keep 7
        level info
    </file>

.. _file_parameters:

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

rotate
    Rotate the log file automatically. Valid options are:

    "hourly" or "hour"
        Rotate the log file every hour

    "daily" or "day"
        Rotate the log file every day

    "weekly" or "week"
        Rotate the log file every week

    "size"
        Rotate the log file based on size

    **Default**: do not rotate based

size
    When rotating based on size a file size must be specified. You can use the suffixed "kb", "mb" or "gb"
    to make the value more readable.

keep
    When rotating log files you must specify how many files to keep.

