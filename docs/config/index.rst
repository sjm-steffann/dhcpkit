IPv6 Server configuration
=========================

This describes the configuration file for DHCPKit. The syntax of this file is loosely based on the Apache
configuration style. It is implemented using `ZConfig <https://pypi.python.org/pypi/ZConfig>`_.

The configuration file consists of :ref:`basic server settings <schema_parameters>`, :ref:`listeners` that
receive messages from the network and some :ref:`handlers` that process the request and generate the response
(possibly surrounded by :ref:`filters` that determine which handlers get applies to which request).

.. toctree::

    config_file

Overview of sections
--------------------

.. toctree::
    :maxdepth: 1

    logging
    map-rule
    statistics

Overview of section types
-------------------------

.. toctree::
    :maxdepth: 2

    duid
    filter_factory
    handler_factory
    leasequery_store
    listener_factory
    loghandler
