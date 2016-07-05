.. _sol-max-rt:

Sol-max-rt
==========

This sections sets the SOL_MAX_RT value that will be sent to the client.


Example
-------

.. code-block:: dhcpkitconf

    <sol-max-rt>
        limit 43200
        always-send yes
    </sol-max-rt>

.. _sol-max-rt_parameters:

Section parameters
------------------

always-send
    Always send this option, even if the client didn't ask for it.

    **Default**: "no"

limit (required)
    Specify the number of seconds to send as MAX_SOL_RT. The value must be between 60 and 86400 seconds.

    **Example**: "21600"

