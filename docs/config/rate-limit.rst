.. _rate-limit:

Rate-limit
==========

The most common reason that clients keep sending requests is when they get
an answer they don't like. The best way to slow them down is to just stop
responding to them.


Example
-------

.. code-block:: dhcpkitconf

    <rate-limit>
        key remote-id
        rate = 5
        per = 30
    </rate-limit>

.. _rate-limit_parameters:

Section parameters
------------------

key
    The key to use to distinguish between clients. By default the DUID is used, but depending on your
    environment a different key may be appropriate. Possible values are:

    - duid
    - interface-id
    - remote-id
    - subscriber-id
    - linklayer-id

    If the chosen key is not available in the incoming request then the rate limiter will automatically
    fall back to identification by DUID.

    **Default**: "duid"

rate
    The number of messages that a client may send per time slot.

    **Default**: "5"

per
    The duration of a time slot in seconds.

    **Default**: "30"

burst
    The burst size allowed.

    **Default**: The same as the rate.

