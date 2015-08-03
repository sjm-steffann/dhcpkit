"""
Setup script for dhcpkit: A DHCP library and server for IPv4 and IPv6 written in Python
"""

from setuptools import find_packages, setup

import dhcpkit

setup(
    name='dhcpkit',
    version=dhcpkit.__version__,

    description='A DHCP library and server for IPv4 and IPv6 written in Python',
    keywords='dhcp server ipv4 ipv6',
    url='https://git.steffann.nl/sjm-steffann/dhcpkit',
    license='BSD',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
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
            'ipv6-dhcpd = dhcp.ipv6.server:run',
        ],
    },

    install_requires=[
        'netifaces',
    ],

    test_suite='tests',

    author='Sander Steffann',
    author_email='sander@steffann.nl',
)
