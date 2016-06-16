"""
Common logging component
"""

# Extra log levels
import logging

DEBUG_PACKETS = 7
DEBUG_HANDLING = 5

logging.addLevelName(DEBUG_PACKETS, 'PACKET')
logging.addLevelName(DEBUG_HANDLING, 'HANDLING')
