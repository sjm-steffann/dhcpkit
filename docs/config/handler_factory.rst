.. _handlers:

Handlers
========

Configuration sections that specify a handler. Handlers process requests, build the response etc.
Some of them add information options to the response, others look up the client in a CSV file
and assign addresses and prefixes, and others can abort the processing and tell the server not to
answer at all.

You can make the server do whatever you want by configuring the appropriate handlers.

.. toctree::

    aftr-name
    copy-linklayer-id
    copy-remote-id
    copy-subscriber-id
    domain-search-list
    iana-timing-limits
    iapd-timing-limits
    ignore-request
    inf-max-rt
    leasequery
    map-e
    map-t
    ntp-servers
    preference
    rate-limit
    recursive-name-servers
    server-unicast
    sip-server-addresses
    sip-server-names
    sntp-servers
    sol-max-rt
    static-csv
    static-sqlite
