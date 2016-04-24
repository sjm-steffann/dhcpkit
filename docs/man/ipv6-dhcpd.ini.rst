ipv6-dhcpd.ini(5)
=================


File format
-----------
The configuration for :doc:`ipv6-dhcpd` is provided as an INI file. Most sections depend on the chosen
:doc:`message handler <../api/dhcpkit.ipv6.message_handlers>`. There are a few sections that apply to all message
handlers. If the default settings are acceptable the ``[server]`` section may be omitted. The configuration does
however need at least one :ref:`interface configuration <interfaces>`.


Basic server configuration
--------------------------
The main server code handles parsing the configuration, setting up logging, creating network sockets, receiving DHCPv6
requests and sending the replies. What happens between receiving the request and sending the reply is up to the chosen
:ref:`message handlers <message_handlers>`.

The default configuration for the server is:

.. code-block:: ini

    [server]
    duid = auto
    message-handler = standard
    user = nobody
    group =
    exception-window = 1.0
    max-exceptions = 10
    threads = 10

.. _server_duid:

duid:
    This is the server DUID value encoded in hexadecimal, or the value ``auto``. When set to ``auto`` the server will
    generate a DUID-LL from the MAC address of the first network interface it listens on.

    For example: if the MAC address is ``00:24:36:ef:1d:89`` then the generated
    :class:`.LinkLayerDUID` will have hex value ``00030001002436ef1d89`` (DUID type ``3``, hardware type ``1``,
    link-layer address ``002436ef1d89``.

message-handler:
    This is the name of the :ref:`message handler <message_handlers>` that will process incoming requests and generate
    the replies. The server will import the module and call the function :func:`handler` in it with a dict with the
    parsed configuration as the only parameter.

    If the import fails and only a module name is given the server will try to import the module from the
    :mod:`dhcpkit.ipv6.message_handlers` package.

user/group:
    The server has to be started as root because it needs to open network sockets on a privileged port. Running as root
    obviously not very safe so the server will drop its root privileges as soon as possible. The `user` and
    `group` settings specify the user and group to switch to. Both numerical values and names can be used. If
    the `group` setting is left empty then the primary group of the given user will be used.

exception-window/max-exceptions:
    The main server loop does not do a lot of work. It mainly receives network packets, parses them and pushes them to
    the worker threads that will handle them. Should something unexpected go wrong there is a small risk that the
    server will end up looping infinitely. To prevent that there is an unexpected exception handler that counts the
    number of exceptions over time. If more than `max-exceptions` exceptions occur within `exception-window` seconds
    then the server process will shut itself down.

threads:
    The server is implemented as a multi-threaded process. Incoming requests are delegated to worker threads that will
    process them. You can vary the number of concurrent worker threads by changing this setting.


.. _logging:

Logging configuration
---------------------
The server will send its log messages to ``syslog`` and optionally (if requested with :option:`ipv6-dhcpd -v`) to the
standard output. The syslog logging facility to log to can be configured. The default is:

.. code-block:: ini

    [logging]
    facility = daemon


.. _interfaces:

Interface configuration
-----------------------
The network interfaces that the server listens on and replies from need to be configured. By default the server does not
listen on any network interface and refuse to start. Network interfaces can be configured as follows:

.. code-block:: ini

    [interface en0]
    global-unicast-addresses = all
    link-local-addresses = auto
    multicast = yes
    listen-to-self = no

The name of the interface (``en0`` in this example) must be an existing interface or the value ``*``. The settings for
``*`` will be applied to all interfaces on the machine that do not have a specific configuration. For example the
following configuration would make the server listen to multicast messages on all interfaces except ``en1``, where it
would only listen for messages on its global unicast addresses:

.. code-block:: ini

    [interface *]
    multicast = yes

    [interface en1]
    global-unicast-addresses = all

global-unicast-addresses:
    Here you can specify the global unicast addresses that the server will listen on. By default it will not listen on
    any address. If you specify ``all`` the server will auto-discover the available global unicast addresses and listen
    on all of them. If you specify ``auto`` the server will try to determine the 'best' one as described below.

link-local-addresses:
    Here you can specify the link-local addresses that the server will listen on. By default it will not listen on
    any address. If you specify ``all`` the server will auto-discover the available link-local addresses and listen
    on all of them. If you specify ``auto`` the server will try to determine the 'best' one as described below.

multicast:
    Determines if the server listens on the well-known DHCPv6-relay-agents-and-servers multicast address
    (``'ff02::1:2'``). This setting is off by default. Because a server cannot send replies from a multicast address
    it needs a link-local address as well. Enabling this option will change the default `link-local-addresses` setting
    from empty to ``auto``.

listen-to-self:
    Usually a server doesn't listen to multicast requests it sends itself. If you want your DHCP server to respond to
    its own requests (usually for testing purposes) then you can enable this option.


Choosing the 'best' address
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The current algorithm for choosing the 'best' address first looks for addresses that have the ``u`` bit set to ``1`` in
the interface-id. Such addresses should have universal scope and should be stable over longer periods of time. They are
usually derived from MAC addresses. If there are multiple addresses then the lowest one will be used.

If no addresses with universal scope are found then the lowest address found on the interface is used.


.. _message_handlers:

Message handlers
----------------
A message handler is responsible for processing incoming messages and constructing appropriate responses. Most of the
time the :ref:`standard message handler <standard_message_handler>` (which is the default) will be used, but in users
can write their own message handlers if required.


.. _standard_message_handler:

Standard message handler
^^^^^^^^^^^^^^^^^^^^^^^^
Implemented in :mod:`dhcpkit.ipv6.message_handlers.standard`.

This is the default message handler. It implements the basics of the DHCPv6 protocol as described in :rfc:`3315`:

- It makes sure that if the client sends a :class:`ServerIdOption <.ServerIdOption>` the server will only respond if the
  value of that option matches its own :class:`.DUID`.
- It adds the :ref:`server's DUID <server_duid>` to any responses the server sends.
- It copies the :class:`.ClientIdOption` from the request to the response.
- It processes all :ref:`option handlers <option_handlers>` specified in this configuration file in the order that they
  were defined. These option handlers perform tasks like assigning addresses to clients and adding information to
  responses. See below for an overview of the standard handlers available.
- It makes sure that every :class:`.IANAOption`, :class:`.IATAOption` and :class:`.IAPDOption` has an appropriate
  response. If no other :ref:`option handler <option_handlers>` provided a response the server will tell the client that
  there are no addresses available.
- It will add the correct :class:`.StatusCodeOption` to the response where required.


.. _dump_requests_message_handler:

Request dumping message handler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Implemented in :mod:`dhcpkit.ipv6.message_handlers.dump_requests`.

This message handler can be used when you want to see which requests clients are sending without actually replying to
them. This handler does nothing more than dump any incoming messages to ``stdout`` in a readable format.


.. _option_handlers:

Option handlers
---------------
Option handlers do the real work for processing DHCPv6 requests. They set or modify options in the response. Examples
of functions performed by option handlers are:

- Assigning addresses or prefixes to clients
- Providing clients with DNS information
- Specifying how often clients should renew their address bindings
- etc.

Many option handlers are provided and users are encouraged to write their own and where useful offer them back to the
community. The currently provided option handlers that can be added by defining them in the configuration file are:

.. toctree::
    ipv6-dhcpd.ini-preference_option
    ipv6-dhcpd.ini-csv-based-fixed-assignment
    ipv6-dhcpd.ini-dns
    ipv6-dhcpd.ini-ntp
    ipv6-dhcpd.ini-sntp
    ipv6-dhcpd.ini-sip-servers
    ipv6-dhcpd.ini-sol-max-rt
    ipv6-dhcpd.ini-server-unicast
    ipv6-dhcpd.ini-timing-limits
    ipv6-dhcpd.ini-unanswered-options
