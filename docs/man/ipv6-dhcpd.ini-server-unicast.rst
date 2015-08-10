Server Unicast option handler
=============================
This option handler adds a :class:`.ServerUnicastOption` to replies where appropriate. It tells client that they are
allowed to contact the server using the provided unicast address instead of using multicast.

.. warning::

    This can potentially cause problems identifying the clients because by using unicast the client will bypass any
    relays. The information provided by those relays might be necessary to provide the correct information to the
    client. Only use this option if you understand the consequences.

An example configuration for this option:

.. code-block:: ini

    [option ServerUnicast]
    server-address = 2001:db8::1
