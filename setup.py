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
            'dhcpkit-generate-config-docs = dhcpkit.ipv6.server.generate_config_docs:run',
            'ipv6-dhcpd = dhcpkit.ipv6.server.main:run',
            'ipv6-dhcp-build-sqlite = dhcpkit.ipv6.server.extensions.static_assignments.sqlite:build_sqlite',
        ],
        'pygments.lexers': [
            'dhcpkitconf = dhcpkit.ipv6.server.pygments_plugin:DHCPKitConfLexer'
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
        'dhcpkit.ipv6.options.ntp.suboptions': [
            '1 = dhcpkit.ipv6.extensions.ntp:NTPServerAddressSubOption',
            '2 = dhcpkit.ipv6.extensions.ntp:NTPMulticastAddressSubOption',
            '3 = dhcpkit.ipv6.extensions.ntp:NTPServerFQDNSubOption',
        ],
        'dhcpkit.ipv6.server.extensions': [
            # Listeners
            'listen-unicast     = dhcpkit.ipv6.server.listeners.unicast',
            'listen-interface   = dhcpkit.ipv6.server.listeners.multicast_interface',

            # DUID elements for the configuration file
            'duid-ll            = dhcpkit.ipv6.server.duids.duid_ll',
            'duid-en            = dhcpkit.ipv6.server.duids.duid_en',
            'duid-llt           = dhcpkit.ipv6.server.duids.duid_llt',

            # Filters
            'elapsed-time       = dhcpkit.ipv6.server.filters.elapsed_time',
            'marks              = dhcpkit.ipv6.server.filters.marks',
            'subnets            = dhcpkit.ipv6.server.filters.subnets',

            # Handlers
            'dns                = dhcpkit.ipv6.server.extensions.dns',
            'ntp                = dhcpkit.ipv6.server.extensions.ntp',
            'prefix-delegation  = dhcpkit.ipv6.server.extensions.prefix_delegation',
            'remote-id          = dhcpkit.ipv6.server.extensions.remote_id',
            'sip                = dhcpkit.ipv6.server.extensions.sip_servers',
            'sntp               = dhcpkit.ipv6.server.extensions.sntp',
            'sol-max-rt         = dhcpkit.ipv6.server.extensions.sol_max_rt',
            'static-assignments = dhcpkit.ipv6.server.extensions.static_assignments',
            'timing-limits      = dhcpkit.ipv6.server.extensions.timing_limits',
        ],
    },
    setup_requires=[
        'sphinx',
        'sphinx-rtd-theme',
    ],
    install_requires=[
        'netifaces',
        'cached_property',
        'ZConfig',
        'typing',
    ],

    test_suite='tests',

    author='Sander Steffann',
    author_email='sander@steffann.nl',

    zip_safe=False,
)
