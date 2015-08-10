Timing Limits option handlers
=============================
There are two versions of this option handler. They modify the T1 and T2 values of respectively all
:class:`.IANAOption` and :class:`.IAPDOption` in the response. Both option handlers accept the same configuration
settings.

If those values are ``0`` (which means: "let the client decide") this option will calculate their value
as a factor of the shortest preferred lifetime of the addresses in this option. If all addresses have an infinite
lifetime then T1 and T2 will also be set to infinity. Factors are specified as a value between ``0.0`` and ``1.0`` or
the word ``NONE``. If automatic calculation of T1 and T2 is disabled the value will stay ``0``. After calculating the
starting values of T1 and T2 the ``min`` and ``max`` settings are applied.

The minimum and maximum values are specified as a number of seconds or the word ``INFINITY``.

.. note::

    Minimum and maximum values will be ignored if they conflict with the protocol or common sense. T1 and T2 will never
    be higher than the shortest preferred lifetime to make sure that clients can renew their addresses in time. T1 will
    also never be higher than T2 as this would invalidate the response.

Example configurations for these options:

.. code-block:: ini

    [option IANATimingLimits]
    min-t1 = 0
    max-t1 = INFINITY
    factor-t1 = 0.5

    min-t2 = 0
    max-t2 = INFINITY
    factor-t2 = 0.8

    [option IAPDTimingLimits]
    max-t1 = 3600
    max-t2 = 7200

The default values for the settings of both ``IANATimingLimits`` and ``IAPDTimingLimits`` are the values shows in the
example for ``IANATimingLimits``.
