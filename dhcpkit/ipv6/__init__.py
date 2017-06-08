"""
Constants relevant for the IPv6 DHCP protocol
"""
from ipaddress import IPv6Address

All_DHCP_Relay_Agents_and_Servers = IPv6Address('ff02::1:2')
All_DHCP_Servers = IPv6Address('ff05::1:3')

CLIENT_PORT = 546
SERVER_PORT = 547

# Transmission and Retransmission Parameters
# :rfc:`3315#section-5.5`
SOL_MAX_DELAY = 1
SOL_TIMEOUT = 1
SOL_MAX_RT = 120
REQ_TIMEOUT = 1
REQ_MAX_RT = 30
REQ_MAX_RC = 10
CNF_MAX_DELAY = 1
CNF_TIMEOUT = 1
CNF_MAX_RT = 4
CNF_MAX_RD = 10
REN_TIMEOUT = 10
REN_MAX_RT = 600
REB_TIMEOUT = 10
REB_MAX_RT = 600
INF_MAX_DELAY = 1
INF_TIMEOUT = 1
INF_MAX_RT = 120
REL_TIMEOUT = 1
REL_MAX_RC = 5
DEC_TIMEOUT = 1
DEC_MAX_RC = 5
REC_TIMEOUT = 2
REC_MAX_RC = 8
HOP_COUNT_LIMIT = 32

# Representation of time values and "Infinity" as a time value
# :rfc:`3315#section-5.6`
INFINITY = 0xffffffff
