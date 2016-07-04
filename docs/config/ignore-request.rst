.. _ignore-request:

Ignore-request
==============

When this handler is activated it tells the server to immediately stop all processing and ignore the
request. The server will not send any response to the client.


Example
-------

.. code-block:: dhcpkitconf

    <ignore-request>
        message-type solicit
    </ignore-request>

.. _ignore-request_parameters:

Section parameters
------------------

message-type (multiple allowed)
    The name of a message type to ignore. Can be for example ``solicit`` or ``information-request``.

    **Default**: Ignore all messages

