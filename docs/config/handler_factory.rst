.. _handlers:

Handlers
========

Configuration sections that specify a handler. Handlers are the things that process requests, build the
response etc. Some of them add information options to the response, others look up the client in a CSV file
and assign addresses and prefixes, and others can abort the processing and tell the server not to answer
at all.

You can make the server do whatever you want by configuring the appropriate handlers.

.. toctree::

    copy-remote-id
    domain-search-list
    ignore-request
    ntp-servers
    recursive-name-servers
    require-multicast
    sntp-servers
    static-csv
    static-sqlite
