from setuptools import find_packages, setup

setup(
    name='python-dhcp',
    version='0.1.0',

    description='A DHCP server for IPv4 and IPv6 written in Python',
    keywords='dhcp server ipv4 ipv6',
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
            'ipv6-dhcpd = dhcp.ipv6.server.run',
        ],
    },

    test_suite='tests',

    author='Sander Steffann',
    author_email='sander@steffann.nl',
)
