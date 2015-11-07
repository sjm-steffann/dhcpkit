Writing custom option handlers
==============================
Writing a custom option handler is, together with :doc:`writing custom options <option>`, the most common way of
customising the dhcpkit server. Option handlers process the incoming message and adapt the outgoing message. There are
many things an option handler could do. Some of the common use cases are:

- assigning addresses/prefixes to incoming :class:`.IANAOption`, :class:`.IATAOption` and :class:`.IAPDOption` requests
  (see e.g. :class:`.CSVBasedFixedAssignmentOptionHandler`)
- providing :class:`.RecursiveNameServersOption` to clients (see :class:`.RecursiveNameServersOptionHandler`)
- limiting the maximum values for T1/T2 so that clients come back often enough for renewal of their addresses (see e.g.
  :class:`.IANATimingLimitsOptionHandler`)

Basic handler structure
-----------------------
All option handlers must be subclasses of :class:`.OptionHandler` or :class:`.RelayOptionHandler`. Each option handler
must be registered so that the server code is aware of their existence.

An option handler usually implements its functionality by overriding the :meth:`~.OptionHandler.handle` method (
or :meth:`~.RelayOptionHandler.handle_relay` in the case of :class:`.RelayOptionHandler`). This method gets a
:class:`.TransactionBundle` as its only parameter ``bundle``.  The bundle contains all the information available about
a  request and the response. Option handlers providing information (e.g. DNS information) commonly look at whether the
client included an :class:`.OptionRequestOption` in its :attr:`~.TransactionBundle.request` and based on that
information decide to add an extra option to the :attr:`~.TransactionBundle.response`.

Because there are several very common patterns here are some base classes you can use:

- :class:`.SimpleOptionHandler` which adds a static option instance to responses
- :class:`.OverwritingOptionHandler` which overwrites all options of the same class with adds a static option instance
- :class:`.CopyOptionHandler` which copies options from a certain class from the request to the response
- :class:`.CopyRelayOptionHandler` which copies options from a certain class from each incoming
  :class:`.RelayForwardMessage` to the corresponding :class:`.RelayReplyMessage`.

Loading handlers from the configuration file
--------------------------------------------
If you want your option handler to be loadable from the configuration file you need to override the
:meth:`~.OptionHandler.from_config` method. This class method gets called whenever an ``[option ...]`` section is
encountered in the configuration file where the ``...`` matches the name of the option handler class (any
"OptionHandler" suffix may be omitted). This method receives two parameters:

- ``section``: the dictionary-like object containing the settings from the configuration
- ``option_handler_id``: any extra text in the section name after the class name

For example this bit of configuration:

.. code-block:: ini

    [option Example extra]
    setting = something

Would call the ``from_config`` method of ``ExampleOptionHandler`` with ``section['setting'] == 'something'`` and
``option_handler_id == 'extra'``.

Registering new option handlers
-------------------------------
New option handlers must be registered so that the server knows which classes are available when parsing the server
configuration. This is done by defining entry points in the setup script:

.. code-block:: python

    setup(
        name='dhcpkit_demo_extension',
        ...
        entry_points={
            'dhcpkit.ipv6.option_handlers': [
                'config-option-name = dhcpkit_demo_extension.package.module:MyOptionHandlerClass',
            ],
        },
    )

More advanced message handling
------------------------------
If necessary an option handler can do :meth:`~.OptionHandler.pre` and :meth:`~.OptionHandler.post` processing. Pre
processing can be useful in cases where an incoming request has to be checked to see if it should be handled at all or
whether processing should be aborted. Post processing can be used for cleaning up, checking that all required options
are included in the response, committing leases to persistent storage etc.

The post processing stage is especially important to option handlers that assign resources. In the
:meth:`~.OptionHandler.handle` method the option handler puts its assignments in the response. That doesn't mean that
that response is actually sent to the client. Another option handler might change the response or abort the processing
later.

Option handlers that have to store state should do that during post processing after verifying the response. If rapid
commit is active the response might even have changed from an :class:`.AdvertiseMessage` to a :class:`.ReplyMessage`.
Option handlers that store data based on whether a resource was only advertised or whether it was actually assigned
must look at the response being sent to determine that.

Handling rapid commit
---------------------
Usually rapid commit is handled by its own built-in option handler. If an option handler does not want a rapid commit
to happen it can set the :attr:`~.TransactionBundle.allow_rapid_commit` attribute of the transaction bundle to False.
The built-in option handler will take that into account when deciding whether it performs a rapid commit or not.

Rules for option handlers that assign resources
-----------------------------------------------
Options meant for assigning addresses and prefixes like :class:`.IANAOption`, :class:`.IATAOption` and
:class:`.IAPDOption` are a bit more complex to handle. The way option handlers are designed in dhcpkit is that each such
option can be handled by one option handler. An option handler that assigns addresses should use these methods to find
those options in the request that haven't been handled yet:

- :meth:`bundle.get_unanswered_ia_options <.TransactionBundle.get_unanswered_ia_options>`
- :meth:`bundle.get_unanswered_iana_options <.TransactionBundle.get_unanswered_iana_options>`
- :meth:`bundle.get_unanswered_iata_options <.TransactionBundle.get_unanswered_iata_options>`
- :meth:`bundle.get_unanswered_iapd_options <.TransactionBundle.get_unanswered_iapd_options>`

After handling an option the option handler must mark that option as handled by calling
:meth:`bundle.mark_handled <.TransactionBundle.mark_handled>` with the handled option as parameter. This will let
option handlers that are executed later know which options still need to be handled.

When handling :class:`.ConfirmMessage`, :class:`.ReleaseMessage` and :class:`.DeclineMessage` the option handler should
behave as follows:

 - It should mark as handled the options that it is responsible for
 - If the confirm/release/decline is successful it should not modify the response
 - If the confirm/release/decline is **not** successful it should put the appropriate options and/or status code in the
   response
 - If a previous option handler has already put a negative status code in the response then that status code should be
   left intact

The :class:`standard message handler <.StandardMessageHandler>` will automatically apply option handlers that check for
any unhandled options and set the status code if it hasn't been set by any other option handler.

Aborting message handling
-------------------------
There are cases where an option handler decides that the current request should not be handled by this server at all.
One example is when a handler determines that the :class:`.ServerIdOption` in the request refers to a difference
:class:`.DUID` than that of the server. In those cases the handler can throw a :class:`.CannotRespondError` exception.
This will stop all processing and prevent a response from being sent to the client.

An option handler should not abort in the post processing phase. When post processing starts all handlers should be able
to assume that the response is finished and that they can rely on the response being sent.

Example of an OptionHandler
---------------------------
This is the implementation of :class:`.RecursiveNameServersOptionHandler`. As you can see most of the code is for
parsing the configuration data so that this option handler can be added through the configuration file as described in
the :ref:`RecursiveNameServersOptionHandler_configuration`. manual page.

.. literalinclude:: ../../dhcpkit/ipv6/option_handlers/dns.py
    :pyobject: RecursiveNameServersOptionHandler

Example of a RelayOptionHandler
-------------------------------
This is the implementation of :class:`.InterfaceIdOptionHandler` which copies :class:`.InterfaceIdOption` from incoming
relay messages to outgoing relay messages. As you can see the implementation is very simple:

.. literalinclude:: ../../dhcpkit/ipv6/option_handlers/remote_id.py
    :pyobject: RemoteIdOptionHandler
