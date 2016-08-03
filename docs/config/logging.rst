.. _logging:

Logging
=======

This section contains the logging configuration. It contains a list of log-handlers that specify where to
send the log entries.


Example
-------

.. code-block:: dhcpkitconf

    <logging>
        <console>
            level debug-handling
            color yes
        </console>

        <syslog />

        log-multiprocessing no
    </logging>

.. _logging_parameters:

Section parameters
------------------

log-multiprocessing
    Enable this if you want logging of process handling. Mostly useful for debugging server code.

    **Default**: "no"

Possible sub-section types
--------------------------

:ref:`Loghandler <loghandler>` (multiple allowed)
    Log-handlers output log entries to somewhere. If you want to send your logs somewhere configure one of
    these. There are log-handlers to show log entries on the console. Send them to a syslog process, server,
    etc.

