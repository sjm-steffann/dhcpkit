.. _iana-timing-limits:

Iana-timing-limits
==================

Automatically set the T1 and T2 timers on IANA Options based on given limits.


Example
-------

.. code-block:: dhcpkitconf

    <iana-timing-limits>
        min-t1 30m
        max-t1 12h
        factor-t1 0.5

        min-t2 30m
        max-t2 1d
        factor-t2 0.8
    </iana-timing-limits>

.. _iana-timing-limits_parameters:

Section parameters
------------------

min-t1
    Minimum value for T1. T1 is the time at which the client contacts the server from which the addresses
    were obtained to extend their lifetimes, specified in seconds after the current time.

    **Default**: "0"

max-t1
    Maximum value for T1. T1 is the time at which the client contacts the server from which the addresses
    were obtained to extend their lifetimes, specified in seconds after the current time.

    **Default**: "INFINITY"

factor-t1
    The default factor for calculating T1 if it hasn't been set already. This is specified as a fraction
    of the shortest lifetime of the addresses in the IANAOption.

    **Default**: "0.5"

min-t2
    Minimum value for T2. T2 is the time at which the client contacts any available server to extend the
    lifetimes of its addresses, specified in seconds after the current time.

    **Default**: "0"

max-t2
    Maximum value for T2. T2 is the time at which the client contacts any available server to extend the
    lifetimes of its addresses, specified in seconds after the current time.

    **Default**: "INFINITY"

factor-t2
    The default factor for calculating T2 if it hasn't been set already. This is specified as a fraction
    of the shortest lifetime of the addresses in the IANAOption.

    **Default**: "0.8"

