About this project
==================

Background
----------
There are plenty of good DHCPv6 servers, but all of them were made for "standard" dynamic environments. During a project at
`Solcon <http://www.solcon.nl/>`_ I found out that something as simple as getting a DHCPv6 server to do some static prefix
delegations to a predetermined set of customers (we were doing a pilot) didn't work with existing tools. I'm constantly on
the lookout for potential blocks to IPv6 deployment to solve, and here was one. Thus, DHCPKit was born.

Sponsors
--------
The first implementation of DHCPKit was partially sponsored by `Solcon <http://www.solcon.nl/>`_, and I am very grateful
for their support. 

After the first version was running in production I decided to take this project further. My goals were:

- Write better documentation
- Improve performance
- Better quality assurance
- Implement more DHCPv6 options
- Add more interfaces, e.g. with RADIUS
- Provide a more flexible configuration file format
- Integrate with monitoring systems

I applied for a grant from the `SIDN Fund <https://www.sidnfonds.nl/excerpt/>`_ to implement all of this. I received the
grant in 2016 and am currently working to achieve these goals.

List of users
-------------
Here is a list of organisations, projects and individuals that have notified me that they are using DHCPKit and want to
be listed here:

- `Solcon <http://www.solcon.nl/>`_

If you are using DHCPKit please let me know by sending an email to dhcpkit@steffann.nl. Please also let me know whether
you want to be mentioned on this page - I will not add any names here without explicit consent.

Participating
-------------
DHCPKit is released under the GPLv3 license so you are free to use and adapt DHCPKit. If you distribute modified or
extended versions of DHCPKit you must honour the license and make your changes available under a compatible license.
If you would like to see extra features and/or options implemented and don't feel like writing the code yourself, please
contact me on dhcpkit@steffann.nl.
