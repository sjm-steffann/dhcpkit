Preference option handler
=========================
This option handler adds a :class:`.PreferenceOption` to replies where appropriate. The DHCPv6 preference option advises
clients on which DHCPv6 server to use when there are multiple servers available. The preference value can be from ``0``
to ``255``. Clients will wait for a little while so they can receive all responses from the different servers before
deciding which one to use. The value ``255`` is special because it tells clients that they don't have to wait and can
use the information from the response immediately.

An example configuration for this option:

.. code-block:: ini

    [option Preference]
    preference = 255
