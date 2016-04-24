Writing custom message handlers
===============================
If the :class:`.StandardMessageHandler` does not do exactly what you want then it is possible to subclass it or to write
your own message handler.

Requirements
------------
Message handlers have a very simple interface:

- The constructor is called with a dictionary with the configuration as the only parameter. It will store that
  configuration in ``self.config``.
- If the configuration changes then it will make sure that no other thread is accessing the config at the same by
  acquiring a writer's lock on its :class:`.RWLock`, update ``self.config`` and call
  :meth:`~.MessageHandler.handle_reload`. You can overrule the ``handle_reload`` method to implement custom
  configuration handling.
- For every incoming request that passes validation the :meth:`~.MessageHandler.handle` method will be called. This
  is where you implement your custom message handling.

  - It's parameters are the received message and whether the request came in over multicast
  - It must return either the outgoing message or ``None`` if no response should be sent

  The server code acts like a software DHCP relay so every incoming message will be wrapped in at least one
  :class:`.RelayForwardMessage` and any response must be wrapped in at least one :class:`.RelayReplyMessage`. This
  provides the :meth:`~.MessageHandler.handle` implementation with information like the source address of the client
  and the name of the interface on which the request was received (using :class:`.InterfaceIdOption`).

  Using the :class:`.TransactionBundle` for handling messages is highly recommended as it will automatically deal with
  the relay messages and without it you won't be able to use option handlers.

.. warning::
    Because the server is multi-threaded you have to acquire the :class:`.RWLock` before accessing the configuration or
    any properties that are updated by your :meth:`~.MessageHandler.handle_reload` code. The best way to do this is
    using the context manager:

    .. code-block:: python

        with self.lock.read_lock():
            etc

Simple example
--------------
One of the simplest possible implementations of a message handler is the :class:`.DumpRequestsMessageHandler`. It
doesn't use the configuration and just prints incoming requests.

.. literalinclude:: ../../dhcpkit/ipv6/message_handlers/dump_requests.py
    :pyobject: DumpRequestsMessageHandler

Complex example
---------------
A more complex example is the :class:`.StandardMessageHandler`. Because the implementation itself is quite large only a
few pieces will be shown. The first piece is the :meth:`~.StandardMessageHandler.handle_reload` method where you can see
how the option handlers are initialised:

.. literalinclude:: ../../dhcpkit/ipv6/message_handlers/standard.py
    :pyobject: StandardMessageHandler.handle_reload

The other piece is the :meth:`~.StandardMessageHandler.handle` method which creates a :class:`.TransactionBundle`,
acquires the lock and applies all the configured option handlers to it.

.. literalinclude:: ../../dhcpkit/ipv6/message_handlers/standard.py
    :pyobject: StandardMessageHandler.handle
