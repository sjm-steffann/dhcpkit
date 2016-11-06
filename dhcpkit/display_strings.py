"""
Dictionaries with names of common elements, like hardware types. Just for display purposes.
"""

# A dictionary of hardware types, for display purposes
hardware_types = {
    0: "Reserved",
    1: "Ethernet",
    2: "Experimental Ethernet",
    3: "Amateur Radio AX.25",
    4: "Proteon ProNET Token Ring",
    5: "Chaos",
    6: "IEEE 802 Networks",
    7: "ARCNET",
    8: "Hyperchannel",
    9: "Lanstar",
    10: "Autonet Short Address",
    11: "LocalTalk",
    12: "LocalNet",
    13: "Ultra link",
    14: "SMDS",
    15: "Frame Relay",
    16: "ATM (JXB2)",
    17: "HDLC",
    18: "Fibre Channel",
    19: "ATM (RFC2225)",
    20: "Serial Line",
    21: "ATM (Mike Burrows)",
    22: "MIL-STD-188-220",
    23: "Metricom",
    24: "IEEE 1394.1995",
    25: "MAPOS",
    26: "Twinaxial",
    27: "EUI-64",
    28: "HIPARP",
    29: "IP and ARP over ISO 7816-3",
    30: "ARPSec",
    31: "IPsec tunnel",
    32: "InfiniBand",
    33: "TIA-102 Project 25 Common Air Interface (CAI)",
    34: "Wiegand Interface",
    35: "Pure IP",
    36: "HW_EXP1",
    37: "HFI",
    256: "HW_EXP2",
    257: "AEthernet",
    65535: "Reserved",
}

# Dictionary describing DHCPv6 status codes
status_codes = {
    0: "Success",
    1: "UnspecFail",
    2: "NoAddrsAvail",
    3: "NoBinding",
    4: "NotOnLink",
    5: "UseMulticast",
    6: "NoPrefixAvail",
    7: "UnknownQueryType",
    8: "MalformedQuery",
    9: "NotConfigured",
    10: "NotAllowed",
    11: "QueryTerminated",
}

# Dictionary describing Leasequery query types
lq_query_types = {
    1: "QueryByAddress",
    2: "QueryByClientId",
    3: "QueryByRelayId",
    4: "QueryByLinkAddress",
    5: "QueryByRemoteId",
}
