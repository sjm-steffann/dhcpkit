"""
Setup script for dhcpkit: A DHCP library and server for IPv4 and IPv6 written in Python
"""
import os

from setuptools import find_packages, setup

import dhcpkit

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname: str) -> str:
    """
    Read the contents of a file

    :param fname: the file name relative to this file
    :return: The contents of the file
    """
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='dhcpkit',
    version=dhcpkit.__version__,

    description='A DHCP library and server for IPv6 written in Python',
    long_description=read('README.rst'),
    keywords='dhcp server ipv6',
    url='https://git.steffann.nl/sjm-steffann/dhcpkit',
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
    ],

    packages=find_packages(exclude=['tests']),
    entry_points={
        'console_scripts': [
            'ipv6-dhcpd = dhcpkit.ipv6.server:run',
        ],
    },

    install_requires=[
        'netifaces',
    ],

    test_suite='tests',

    author='Sander Steffann',
    author_email='sander@steffann.nl',
)
