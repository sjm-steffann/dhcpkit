Developer's guide
=================

.. warning::
    Remember that the dhcpkit server is multi-threaded. All implementations must be thread-safe.

Adapting dhcpkit to your needs might require some custom development. There are several areas where you can customise
the server's behaviour:

.. toctree::

    option_handler
    option
    message_handler
