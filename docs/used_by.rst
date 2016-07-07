About this project
==================

Background
----------
I started this project because I am constantly looking for things that block IPv6 deployment. During a project at
`Solcon <http://www.solcon.nl/>`_ I found that there was no good DHCPv6 server that could be used in their environment.
There are plenty of good DHCPv6 servers, but all of them were made for "standard" dynamic environments. A DHCPv6 server
to i.e. just do some static prefix delegations to a predetermined set of customers (we were doing a pilot) didn't work.
And that is how I found the next "blocker" that I was going to solve, and DHCPKit is the result.

Sponsors
--------
The first implementation of DHCPKit was partially sponsored by `Solcon <http://www.solcon.nl/>`_, and I am very grateful
for their support. After the first version was running in production I decided to take this project further and set
myself some goals:

- Write better documentation
- Improve performance
- Better quality assurance
- Implement more DHCPv6 options
- Add more interfaces, e.g. with RADIUS
- Provide a more flexible configuration file format
- Integrate with monitoring systems

I applied for a grant from the `SIDN Fund <https://www.sidnfonds.nl/excerpt/>`_ to implement all of this. I received the
grant in 2016 and am currently working to reach these goals.

List of users
-------------
Here is a list of organisations, projects and individuals that have notified me that they are using DHCPKit and want to
be listed here:

- `Solcon <http://www.solcon.nl/>`_

If you are using DHCPKit please let me know by sending an email to dhcpkit@steffann.nl. Please let me know if you want
to be mentioned on this page because I will not add any names here without explicit consent.

Participating
-------------
DHCPKit is released under the GPLv3 license so you are free to use and adapt DHCPKit. If you distribute modified or
extended versions of DHCPKit you must honor the license and make your changes available under a compatible license.
If you would like to see extra features and/or options implemented and don't feel like writing the code yourself please
contact me on dhcpkit@steffann.nl.
