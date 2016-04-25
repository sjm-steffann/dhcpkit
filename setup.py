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
def read(filename):
    """
    Read the contents of a file

    :param filename: the file name relative to this file
    :return: The contents of the file
    """
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name='dhcpkit',
    version=dhcpkit.__version__,

    description='A DHCP library and server for IPv6 written in Python',
    long_description=read('README.rst'),
    keywords='dhcp server ipv6',
    url='https://github.com/sjm-steffann/dhcpkit',
    license='GPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
    ],

    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ipv6-dhcpd = dhcpkit.ipv6.server:run',
            'ipv6-dhcp-build-shelf = dhcpkit.ipv6.option_handlers.shelf:create_shelf_from_csv',
            'ipv6-dhcp-build-sqlite = dhcpkit.ipv6.option_handlers.sqlite:create_sqlite_from_csv',
        ],
        'dhcpkit.ipv6.messages': [
            '1 = dhcpkit.ipv6.messages:SolicitMessage',
            '2 = dhcpkit.ipv6.messages:AdvertiseMessage',
            '3 = dhcpkit.ipv6.messages:RequestMessage',
            '4 = dhcpkit.ipv6.messages:ConfirmMessage',
            '5 = dhcpkit.ipv6.messages:RenewMessage',
            '6 = dhcpkit.ipv6.messages:RebindMessage',
            '7 = dhcpkit.ipv6.messages:ReplyMessage',
            '8 = dhcpkit.ipv6.messages:ReleaseMessage',
            '9 = dhcpkit.ipv6.messages:DeclineMessage',
            '10 = dhcpkit.ipv6.messages:ReconfigureMessage',
            '11 = dhcpkit.ipv6.messages:InformationRequestMessage',
            '12 = dhcpkit.ipv6.messages:RelayForwardMessage',
            '13 = dhcpkit.ipv6.messages:RelayReplyMessage',
        ],
        'dhcpkit.ipv6.duids': [
            '1 = dhcpkit.ipv6.duids:LinkLayerTimeDUID',
            '2 = dhcpkit.ipv6.duids:EnterpriseDUID',
            '3 = dhcpkit.ipv6.duids:LinkLayerDUID',
        ],
        'dhcpkit.ipv6.options': [
            '1 = dhcpkit.ipv6.options:ClientIdOption',
            '2 = dhcpkit.ipv6.options:ServerIdOption',
            '3 = dhcpkit.ipv6.options:IANAOption',
            '4 = dhcpkit.ipv6.options:IATAOption',
            '5 = dhcpkit.ipv6.options:IAAddressOption',
            '6 = dhcpkit.ipv6.options:OptionRequestOption',
            '7 = dhcpkit.ipv6.options:PreferenceOption',
            '8 = dhcpkit.ipv6.options:ElapsedTimeOption',
            '9 = dhcpkit.ipv6.options:RelayMessageOption',
            '11 = dhcpkit.ipv6.options:AuthenticationOption',
            '12 = dhcpkit.ipv6.options:ServerUnicastOption',
            '13 = dhcpkit.ipv6.options:StatusCodeOption',
            '14 = dhcpkit.ipv6.options:RapidCommitOption',
            '15 = dhcpkit.ipv6.options:UserClassOption',
            '16 = dhcpkit.ipv6.options:VendorClassOption',
            '17 = dhcpkit.ipv6.options:VendorSpecificInformationOption',
            '18 = dhcpkit.ipv6.options:InterfaceIdOption',
            '19 = dhcpkit.ipv6.options:ReconfigureMessageOption',
            '20 = dhcpkit.ipv6.options:ReconfigureAcceptOption',
            '21 = dhcpkit.ipv6.extensions.sip_servers:SIPServersDomainNameListOption',
            '22 = dhcpkit.ipv6.extensions.sip_servers:SIPServersAddressListOption',
            '23 = dhcpkit.ipv6.extensions.dns:RecursiveNameServersOption',
            '24 = dhcpkit.ipv6.extensions.dns:DomainSearchListOption',
            '25 = dhcpkit.ipv6.extensions.prefix_delegation:IAPDOption',
            '26 = dhcpkit.ipv6.extensions.prefix_delegation:IAPrefixOption',
            '31 = dhcpkit.ipv6.extensions.sntp:SNTPServersOption',
            '37 = dhcpkit.ipv6.extensions.remote_id:RemoteIdOption',
            '56 = dhcpkit.ipv6.extensions.ntp:NTPServersOption',
            '82 = dhcpkit.ipv6.extensions.sol_max_rt:SolMaxRTOption',
            '83 = dhcpkit.ipv6.extensions.sol_max_rt:InfMaxRTOption',
        ],
        'dhcpkit.ipv6.option_handlers': [
            'preference = dhcpkit.ipv6.option_handlers.basic:PreferenceOptionHandler',
            'server-unicast = dhcpkit.ipv6.option_handlers.basic:ServerUnicastOptionHandler',
            'remote-id = dhcpkit.ipv6.option_handlers.remote_id:RemoteIdOptionHandler',
            'sol-max-rt = dhcpkit.ipv6.option_handlers.sol_max_rt:SolMaxRTOptionHandler',
            'inf-max-rt = dhcpkit.ipv6.option_handlers.sol_max_rt:InfMaxRTOptionHandler',
            'recursive-name-servers = dhcpkit.ipv6.option_handlers.dns:RecursiveNameServersOptionHandler',
            'domain-search-list = dhcpkit.ipv6.option_handlers.dns:DomainSearchListOptionHandler',
            'ntp-servers = dhcpkit.ipv6.option_handlers.ntp:NTPServersOptionHandler',
            ('sip-servers-domain-name-list = '
             'dhcpkit.ipv6.option_handlers.sip_servers:SIPServersDomainNameListOptionHandler'),
            'sip-servers-address-List = dhcpkit.ipv6.option_handlers.sip_servers:SIPServersAddressListOptionHandler',
            'sntp-servers = dhcpkit.ipv6.option_handlers.sntp:SNTPServersOptionHandler',
            'iana-timing-limits = dhcpkit.ipv6.option_handlers.timing_limits:IANATimingLimitsOptionHandler',
            'iapd-timing-limits = dhcpkit.ipv6.option_handlers.timing_limits:IAPDTimingLimitsOptionHandler',
            'csv-based-fixed-assignment = dhcpkit.ipv6.option_handlers.csv:CSVBasedFixedAssignmentOptionHandler',
            'shelf-based-fixed-assignment = dhcpkit.ipv6.option_handlers.shelf:ShelfBasedFixedAssignmentOptionHandler',
            ('sqlite-based-fixed-assignment = '
             'dhcpkit.ipv6.option_handlers.sqlite:SqliteBasedFixedAssignmentOptionHandler'),
        ],
    },
    setup_requires=[
        'sphinx',
        'sphinx-rtd-theme',
    ],
    install_requires=[
        'netifaces',
    ],

    test_suite='tests',

    author='Sander Steffann',
    author_email='sander@steffann.nl',

    zip_safe=False,
)
