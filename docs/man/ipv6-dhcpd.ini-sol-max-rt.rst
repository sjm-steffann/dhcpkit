SOL-MAX-RT option handler
=========================
This option handler adds a :class:`.SolMaxRTOption` to replies where appropriate. In cases where not all clients get an
IPv6 address or prefix (yet) the clients that don't get a reply can put a large strain on the server by retrying over
and over again to get resources. This options can tell such clients to lower the rate that they send
:class:`.SolicitMessage` by increasing the value of :rfc:`SOL_MAX_RT <3315#section-5.5>` in the client.

An example configuration for this option:

.. code-block:: ini

    [option SolMaxRT]
    sol-max-rt = 1800

INF-MAX-RT option handler
=========================
This option handler adds a :class:`.InfMaxRTOption` to replies where appropriate. In cases where not all clients get
IPv6 information the clients that don't get a reply can put a large strain on the server by retrying over and over again
to get answers. This options can tell such clients to lower the rate that they send :class:`.InformationRequestMessage`
by increasing the value of :rfc:`INF_MAX_RT <3315#section-5.5>` in the client.

An example configuration for this option:

.. code-block:: ini

    [option InfMaxRT]
    inf-max-rt = 1800
