.. _inf-max-rt:

Inf-max-rt
==========

This sections sets the INF_MAX_RT value that will be sent to the client. Specify the number of seconds to
send as the section name. The value must be between 60 and 86400 seconds.


Example
-------

.. code-block:: dhcpkitconf

    <inf-max-rt>
        limit 43200
        always-send yes
    </inf-max-rt>

.. _inf-max-rt_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

limit (required)
    Specify the number of seconds to send as INF_SOL_RT. The value must be between 60 and 86400 seconds.

    **Example**: "21600"

