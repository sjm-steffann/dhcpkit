DHCPKit
=======

This package contains a flexible DHCP server written in Python 3.4+. This is not a simple plug-and-play DHCP server.
Its purpose is to provide a framework for DHCP services. It was written for ISPs to use in provisioning their customers
according to their own business rules. It can be integrated into existing ISP management and provisioning tools.

Currently only the IPv6 version is implemented.

Backwards compatibility notice!
-------------------------------

Versions up to and including 0.8.x used .ini files for configuration. Starting in version 0.9.0 this will change to
Apache-style configuration based on ZConfig. This provides the huge advantage that sections can be nested and that
better type checking and error messages are possible. It does however cause old configuration files to stop working.
A conversion tool will be provided, but **please pay attention when upgrading!**

Documentation
-------------

.. image:: http://readthedocs.org/projects/dhcpkit/badge/?version=stable
  :target: http://dhcpkit.readthedocs.org/en/stable/?badge=stable


Build status
------------

.. image:: https://travis-ci.org/sjm-steffann/dhcpkit.svg?branch=master
  :target: https://travis-ci.org/sjm-steffann/dhcpkit

.. image:: https://coveralls.io/repos/sjm-steffann/dhcpkit/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/sjm-steffann/dhcpkit?branch=master


Distribution status
-------------------

.. image:: https://img.shields.io/pypi/v/dhcpkit.svg
  :target: https://pypi.python.org/pypi/dhcpkit

.. image:: https://img.shields.io/pypi/status/dhcpkit.svg
  :target: https://pypi.python.org/pypi/dhcpkit

.. image:: https://img.shields.io/pypi/l/dhcpkit.svg
  :target: https://pypi.python.org/pypi/dhcpkit

.. image:: https://img.shields.io/pypi/pyversions/dhcpkit.svg
  :target: https://pypi.python.org/pypi/dhcpkit

.. image:: https://img.shields.io/pypi/dw/dhcpkit.svg
  :target: https://pypi.python.org/pypi/dhcpkit
