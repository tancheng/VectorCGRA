#=========================================================================
# status_type.py
#=========================================================================
# Status types for CGRA.
#
# Author : Yufei Yang
#   Date : Aug 13, 2025

#-------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------

from pymtl3 import *

# Total number of status.
# Needs to be updated once more status are added/supported.
NUM_STATUS = 4

STATUS_IDLE                       = 0
STATUS_PRESERVING                 = 1
STATUS_RESUMING                   = 2
STATUS_PAUSING                    = 3
