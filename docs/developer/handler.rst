Writing custom handlers
=======================
Writing a custom handler is, together with :doc:`writing custom options <option>`, the most common way of customising
the DHCPKit server. Handlers process the incoming message and adapt the outgoing message. There are many things a
handler could do. Some of the common use cases are:

- assigning addresses/prefixes to incoming :class:`.IANAOption`, :class:`.IATAOption` and :class:`.IAPDOption` requests
  (see e.g. :class:`.CSVStaticAssignmentHandler`)
- providing :class:`.RecursiveNameServersOption` to clients (see :class:`.RecursiveNameServersOptionHandler`)
- limiting the maximum values for T1/T2 so that clients come back often enough for renewal of their addresses (see e.g.
  :class:`.IANATimingLimitsHandler`)

Basic handler structure
-----------------------
All handlers must be subclasses of :class:`.Handler` or :class:`.RelayHandler`. Each handler must be
registered as a server extension so that the server code is aware of their existence.

A handler usually implements its functionality by overriding the :meth:`~.Handler.handle` method (or
:meth:`~.RelayHandler.handle_relay` in the case of :class:`.RelayHandler`). This method gets a
:class:`.TransactionBundle` as its only parameter ``bundle``.  The bundle contains all the information available about
a  request and the response. Handlers providing information (e.g. DNS information) commonly look at whether the
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
There are two parts to creating new handlers that can be used in the configuration file. The first part is 
the XML definition of what the configuration section looks like. The second part is a factory function
or object that will create the handler from the configuration.

Defining the configuration section
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If you want your handler to be loadable from the configuration file you need to provide a :mod:`ZConfig`
``component.xml`` schema file that determines what your configuration section will look like. A configuration section
definition can look like this:

.. literalinclude:: ../../dhcpkit/ipv6/server/extensions/dns/component.xml
    :language: xml

This component describes two section types: ``recursive-name-servers`` and ``domain-search-list``. They both have
``implements="handler_factory"`` which makes them usable as a handler. The datatypes of the sections are relative to
``prefix="dhcpkit.ipv6.server.extensions.dns.config"`` because they start with a ``.``.

The datatypes of ``<key>`` and ``<multikey>`` elements can be one of the ZConfig predefined types or anything that can
be called like a function which accepts the string value of what the user put into the configuration file as its single
parameter. Its return value is stored as the value. This behaviour also allows you to provide a class as the datatype.
Its constructor will be called with a single string argument. In the example above you can see this for the
``<multikey name="address" ...`` where the datatype is the :class:`~ipaddress.IPv6Address` class from :mod:`ipaddress`.

The ``<description>`` and ``<example>`` tags are used when generating documentation. The whole :doc:`configuration
section </config/index>` of this manual is created based on such tags!

Writing the handler factory
^^^^^^^^^^^^^^^^^^^^^^^^^^^
After parsing a section and converting its values using the specified datatypes, the datatype of the sectiontype will
be called with a :class:`ZConfig.SectionValue` object containing all the values as its only parameter. The return value
of that datatype must be callable as a function, which acts as a factory for the actual handler.

.. note::

    The reason that a factory is used is for privilege separation. The configuration file is read as the user that
    started the server process, usually ``root``, while the factory is called with the privileges of the user and
    group that the server is configured to run as. This makes sure that e.g. all files created by a handler have the
    right ownership.

The easiest way to write a handler factory is to create a subclass of :class:`.HandlerFactory` and create the
:class:`.Handler` in the implementation of the :meth:`~.ConfigElementFactory.create` method. Because
:class:`.HandlerFactory` is a subclass of :class:`.ConfigSection` you can use its functionality to assist with
processing configuration sections. If some of the values in the configuration are optional and the default value has to
be determined at runtime you can modify :attr:`~.ConfigSection.section` in :meth:`~.ConfigSection.clean_config_section`.
If the configuration values need extra validation then do so in :meth:`~.ConfigSection.validate_config_section`.
For convenience you can access the configuration values both as `self.section.xyz` and as `self.xyz`.

If you want your section to have a "name" like in:

.. code-block:: dhcpkitconf

    <static-csv data/assignments.csv>
        prefix-preferred-lifetime 3d
        prefix-valid-lifetime 30d
    </static-csv>

You can set the :attr:`~dhcpkit.common.server.config_elements.ConfigSection.name_datatype` to the function or class
that should be used to parse the name.

This is a complete example that uses both the name and other section values:

.. literalinclude:: ../../dhcpkit/ipv6/server/extensions/static_assignments/config.py
    :pyobject: CSVStaticAssignmentHandlerFactory

Handler initialisation
----------------------
Handlers are initialised in two steps. The first step is when the factory creates the handler object. This happens in
the main server process just before the worker processes are spawned. Those worker processes get a copy of the handlers
when the worker is being initialised. This is done by :mod:`pickling <pickle>` the :class:`.MessageHandler` and all
the filters and handlers it contains. The advantage is that workers don't need to initialise everything themselves
(especially if that initialisation can take a long time, like when parsing a CSV file) but it also means that things
that cannot be pickled can therefore not be initialised when creating the handler. Therefore handlers have a separate
:meth:`~.Handler.worker_init` method that is called inside each worker. Initialisation that need to happen in each worker
process (for example opening database connections) can be done there.

Registering new handlers
------------------------
New handlers must be registered so that the server knows which sections are available when parsing the server
configuration. This is done by defining entry points in the setup script:

.. code-block:: python

    setup(
        name='dhcpkit_demo_extension',
        ...
        entry_points={
            'dhcpkit.ipv6.server.extensions': [
                'handler-name = dhcpkit_demo_extension.package',
            ],
        },
    )

If the package contains a file called ``component.xml`` then that file is used as an extension to the configuration
file syntax.

More advanced message handling
------------------------------
If necessary a handler can do :meth:`~.Handler.pre` and :meth:`~.Handler.post` processing. Pre processing can be useful
in cases where an incoming request has to be checked to see if it should be handled at all or whether processing should
be aborted. Post processing can be used for cleaning up, checking that all required options are included in the
response, committing leases to persistent storage, etc.

The post processing stage is especially important to handlers that assign resources. In the :meth:`~.Handler.handle`
method the handler puts its assignments in the response. That doesn't mean that that response is actually sent to the
client. Another handler might change the response or abort the processing later.

Handlers that have to store state should do that during post processing after verifying the response. If rapid
commit is active the response might even have changed from an :class:`.AdvertiseMessage` to a :class:`.ReplyMessage`.
Handlers that store data based on whether a resource was only advertised or whether it was actually assigned
must look at the response being sent to determine that.

Handling rapid commit
---------------------
Usually rapid commit is handled by its own built-in handler. If a handler does not want a rapid commit
to happen it can set the :attr:`~.TransactionBundle.allow_rapid_commit` attribute of the transaction bundle to False.
The built-in handler will take that into account when deciding whether it performs a rapid commit or not.

Rules for handlers that assign resources
----------------------------------------
Options meant for assigning addresses and prefixes like :class:`.IANAOption`, :class:`.IATAOption` and
:class:`.IAPDOption` are a bit more complex to handle. The way handlers are designed in dhcpkit is that each such
option can be handled by one handler. A handler that assigns addresses should use the
:meth:`bundle.get_unhandled_options <.TransactionBundle.get_unhandled_options>` method to find those options in the
request that haven't been handled yet:

After handling an option the handler must mark that option as handled by calling
:meth:`bundle.mark_handled <.TransactionBundle.mark_handled>` with the handled option as parameter. This will let
handlers that are executed later know which options still need to be handled.

When handling :class:`.ConfirmMessage`, :class:`.ReleaseMessage` and :class:`.DeclineMessage` the handler should
behave as follows:

 - It should mark as handled the options that it is responsible for
 - If the confirm/release/decline is successful it should not modify the response
 - If the confirm/release/decline is **not** successful it should put the appropriate options and/or status code in the
   response
 - If a previous handler has already put a negative status code in the response then that status code should be
   left intact

The :class:`built-in message handler <.MessageHandler>` will automatically apply handlers that check for any unhandled
options and set the status code if it hasn't been set by any other handler.

Aborting message handling
-------------------------
There are cases where a handler decides that the current request should not be handled by this server at all.
One example is when a handler determines that the :class:`.ServerIdOption` in the request refers to a difference
:class:`.DUID` than that of the server. In those cases the handler can throw a :class:`.CannotRespondError` exception.
This will stop all processing and prevent a response from being sent to the client.

A handler should not abort in the post processing phase. When post processing starts all handlers should be able
to assume that the response is finished and that they can rely on the response being sent.

Example of a Handler
--------------------
This is the implementation of :class:`.RecursiveNameServersOptionHandler`. As you can see most of the code is for
processing the configuration data so that this handler can be added through the configuration file as described in
the :ref:`recursive-name-servers` manual page.

.. literalinclude:: ../../dhcpkit/ipv6/server/extensions/dns/__init__.py
    :pyobject: RecursiveNameServersOptionHandler

Example of a RelayHandler
-------------------------
This is the implementation of :class:`.InterfaceIdOptionHandler` which copies :class:`.InterfaceIdOption` from incoming
relay messages to outgoing relay messages. The implementation is very simple:

.. literalinclude:: ../../dhcpkit/ipv6/server/handlers/interface_id.py
    :pyobject: InterfaceIdOptionHandler
