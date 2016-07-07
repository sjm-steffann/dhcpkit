Writing custom options
======================
Implementing new options usually comes down to writing a new :class:`.Option` class to store the option's content, 
validate the option's contents, and parse and generate the bytes that represent the option on the wire.

Class properties
----------------
Each option class must have a property that defines the option type code implemented by the class. The `list of
option codes <http://www.iana.org/assignments/dhcpv6-parameters/>`_ is maintained by `IANA <http://www.iana.org/>`_. A
common way of setting the option type code is by defining a constant for the code and then using that in the class
definition for readability:

.. code-block:: python

    OPTION_DNS_SERVERS = 23

    class RecursiveNameServersOption(Option):
        option_type = OPTION_DNS_SERVERS

Constructor and properties
--------------------------
Because an option (any :class:`.ProtocolElement`) is defined by its type and contents, the constructor
must reflect that: all relevant properties must correspond to parameters of the option's constructor. This requirement
makes it possible to automate comparison of protocol elements and to print their state in a readable
:meth:`~object.__str__` and parseable :meth:`~object.__repr__` format.

An example is :meth:`.RecursiveNameServersOption.__init__`. As you can see ``dns_servers`` is both the name of the
constructor parameter as the name of the state variable:

.. literalinclude:: ../../dhcpkit/ipv6/extensions/dns.py
    :pyobject: RecursiveNameServersOption.__init__

Validation
----------
Next is the validation. Each option must be able to verify if its state is acceptable and can be encoded to bytes that
can be sent on the wire.

.. note::
    Additionally the validator may make sure that the information makes sense, but be aware that incoming messages that
    violate these checks will be rejected before even reaching the message handler, so make sure that is what you want.

An example is :meth:`.RecursiveNameServersOption.validate` which checks that
:attr:`~.RecursiveNameServersOption.dns_servers` is a list of :class:`~.ipaddress.IPv6Address`:

.. literalinclude:: ../../dhcpkit/ipv6/extensions/dns.py
    :pyobject: RecursiveNameServersOption.validate

Parsing and generating binary representation
--------------------------------------------
These are the most complex parts of an :class:`.Option` implementation. The :meth:`~.ProtocolElement.load_from` method
must be able to parse valid binary representations of the option. Its parameters are a string of bytes and an optional
offset and length. It should start parsing at the specified offset and read up to the specified length from the buffer.
The :meth:`~.ProtocolElement.load_from` method must return the number of bytes that it has used/parsed so that the
caller knows which offset to give to any subsequent option parsers.

All options start with the same fields, which include the option type and the length of the option. That part is called
the option header and is parsed with :meth:`~.Option.parse_option_header`. This will automatically make sure that the
``length`` the caller provided is enough to contain this option's data.

An option parser should make sure that all read data is verified and that all the data up to the option length is read
and parsed. After parsing the data the properties of the object should correspond to the binary string's contents.

Here is the implementation of :meth:`.RecursiveNameServersOption.load_from`:

.. literalinclude:: ../../dhcpkit/ipv6/extensions/dns.py
    :pyobject: RecursiveNameServersOption.load_from

The reverse operation of :meth:`~.ProtocolElement.load_from` is :meth:`~.ProtocolElement.save`. It should generate
bytes to represent its properties. Here is the implementation of :meth:`.RecursiveNameServersOption.save`:

.. literalinclude:: ../../dhcpkit/ipv6/extensions/dns.py
    :pyobject: RecursiveNameServersOption.save

.. note::
    Determining which option type is next in the incoming bytes, creating the right object for it and then loading its
    state with :meth:`~.ProtocolElement.load_from` from bytes is so common that there is a shortcut for that:
    :meth:`~.ProtocolElement.parse`. This uses the option registry to determine the correct object class. See
    :meth:`.Option.determine_class`.

.. note::
    :meth:`~.ProtocolElement.load_from` must be able to parse all valid binary representations of the option.
    Calling :meth:`~.ProtocolElement.save` should produce the original binary representation again. The following should
    be true:

    .. code-block:: python

        # A RecursiveNameServersOption:
        from dhcpkit.ipv6.options import Option
        from dhcpkit.ipv6.extensions.dns import RecursiveNameServersOption

        binary_representation = b'\x00\x17\x00 ' \
            b' \x01H`H`\x00\x00\x00\x00\x00\x00\x00\x00\x88\x88' \
            b' \x01H`H`\x00\x00\x00\x00\x00\x00\x00\x00\x88D'

        read_bytes, parsed_option = Option.parse(binary_representation)
        assert type(parsed_option) == RecursiveNameServersOption
        assert binary_representation == parsed_option.save()

Registering new options
-----------------------
New options must be registered so that the server knows which classes are available for parsing DHCP options. This is
done by defining entry points in the setup script:

.. code-block:: python

    setup(
        name='dhcpkit_demo_extension',
        ...
        entry_points={
            'dhcpkit.ipv6.options': [
                '65535 = dhcpkit_demo_extension.package.module:MyOptionClass',
            ],
        },
    )

Each protocol element also keeps track of which (sub)options it may contain. According to :rfc:`3646#section-5` the
recursive name servers option may appear in Solicit, Advertise, Request, Renew, Rebind, Information-Request, and  Reply
messages. We need to let the classes for those messages know that they may contain this option:

.. code-block:: python

    SolicitMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
    AdvertiseMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
    RequestMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
    RenewMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
    RebindMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
    InformationRequestMessage.add_may_contain(RecursiveNameServersOption, 0, 1)
    ReplyMessage.add_may_contain(RecursiveNameServersOption, 0, 1)

Here we have specified that the RecursiveNameServersOption has a ``min_occurrence`` of ``0`` and a ``max_occurrence``
of ``1`` in each of these message types. If no ``min_occurrence`` and ``max_occurrence`` are specified when calling
:meth:`~.ProtocolElement.add_may_contain` they default to ``0`` and ``infinite`` respectively.
