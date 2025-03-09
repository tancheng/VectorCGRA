#=========================================================================
# cmd_type.py
#=========================================================================
# Commond types for single-/multi-CGRAs.
#
# Author : Cheng Tan
#   Date : Dec 8, 2024

#-------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------

from pymtl3 import *

CMD_LAUNCH        = 0
CMD_PAUSE         = 1
CMD_TERMINATE     = 2
CMD_CONFIG        = 3
CMD_LOAD_REQUEST  = 4
CMD_LOAD_RESPONSE = 5
CMD_STORE_REQUEST = 6
CMD_CONST         = 7
NUM_OPTS = 64
NUM_CMDS = 6

CMD_SYMBOL_DICT = {
  CMD_LAUNCH:        "(LAUNCH_KERNEL)",
  CMD_PAUSE:         "(PAUSE_EXECUTION)",
  CMD_TERMINATE:     "(TERMINATE_EXECUTION)",
  CMD_CONFIG:        "(PRELOADING_KERNEL_CONFIG)",
  CMD_LOAD_REQUEST:  "(LOAD_REQUEST)",
  CMD_LOAD_RESPONSE: "(LOAD_RESPONSE)",
  CMD_STORE_REQUEST: "(STORE_REQUEST)",
  CMD_CONST:         "(CONST_DATA)"
}

