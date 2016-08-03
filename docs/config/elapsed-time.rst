.. _elapsed-time:

Elapsed-time
============

Filter incoming messages based on the value of the :class:`.ElapsedTimeOption` in the request. At least one
time limit must be provided.

This filter can be used as a very simple mechanism for DHCPv6 server fail-over. You can configure one server
without an elapsed-time filter and another server with a filter that ignores solicit messages when the
elapsed time is less than a certain value. The first server will try to answer all request, but if it
doesn't answer all requests for some reason then the client's elapsed time will increase until it passes the
threshold of the second server, which will then stop ignoring it and respond.


Example
-------

.. code-block:: dhcpkitconf

    <elapsed-time>
        less-than 30s

        <ignore-request>
            message-type solicit
        </ignore-request>
    </elapsed-time>

.. _elapsed-time_parameters:

Section parameters
------------------

more-than
    Only process messages where the elapsed time is more than the provided number of seconds. For ease of
    use these suffixes may be used: 's' (seconds), 'm' (minutes), 'h' (hours), or 'd' (days).

    **Example**: "30s"

less-than
    Only process messages where the elapsed time is less than the provided number of seconds. For ease of
    use these suffixes may be used: 's' (seconds), 'm' (minutes), 'h' (hours), or 'd' (days).

    **Example**: "1h"

Possible sub-section types
--------------------------

:ref:`Filters <filters>` (multiple allowed)
    Configuration sections that specify filters. A filter limits which handlers get applied to which messages.
    Everything inside a filter gets ignored if the filter condition doesn't match. That way you can configure
    the server to only apply certain handlers to certain messages, for example to return different information
    options to different clients.

:ref:`Handlers <handlers>` (multiple allowed)
    Configuration sections that specify a handler. Handlers process requests, build the response etc.
    Some of them add information options to the response, others look up the client in a CSV file
    and assign addresses and prefixes, and others can abort the processing and tell the server not to
    answer at all.

    You can make the server do whatever you want by configuring the appropriate handlers.

