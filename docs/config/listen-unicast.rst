.. _listen-unicast:

Listen-unicast
==============

This listener listens to the unicast address specified as the name of the section. This is useful when
you configure a DHCP relay to forward requests to this server.


Example
-------

.. code-block:: dhcpkitconf

    <listen-unicast 2001:db8::1:2 />

.. _listen-unicast_parameters:

Section parameters
------------------

mark (multiple allowed)
    Every incoming request can be marked with different tags. That way you can handle messages differently
    based on i.e. which listener they came in on. Every listener can set one or more marks. Also see the
    :ref:`marked-with` filter.

    **Default**: "unmarked"

