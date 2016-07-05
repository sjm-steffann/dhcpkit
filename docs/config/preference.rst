.. _preference:

Preference
==========

This handler adds a preference level to the response.


Example
-------

.. code-block:: dhcpkitconf

    <preference>
        level 255
    </preference>

.. _preference_parameters:

Section parameters
------------------

level (required)
    The preference level. Higher is better. Preference 255 tells the client that it doesn't have to wait
    for other DHCPv6 servers anymore and that it should request from this server immediately.

