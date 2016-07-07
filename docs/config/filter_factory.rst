.. _filters:

Filters
=======

Configuration sections that specify filters. A filter limits which handlers get applied to which messages.
Everything inside a filter gets ignored if the filter condition doesn't match. That way you can configure
the server to only apply certain handlers to certain messages, for example to return different information
options to different clients.

.. toctree::

    elapsed-time
    marked-with
    subnet
    subnet-group
