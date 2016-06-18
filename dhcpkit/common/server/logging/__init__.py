"""
Common logging component
"""

# Extra log levels
import logging

DEBUG_HANDLING = 7
DEBUG_PACKETS = 5

logging.addLevelName(DEBUG_PACKETS, 'PACKET')
logging.addLevelName(DEBUG_HANDLING, 'HANDLING')
