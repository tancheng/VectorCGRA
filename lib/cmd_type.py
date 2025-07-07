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

# Total number of commands that are supported/recognized by controller.
# Needs to be updated once more commands are added/supported.
NUM_CMDS = 14

CMD_LAUNCH                           = 0
CMD_PAUSE                            = 1
CMD_TERMINATE                        = 2
CMD_CONFIG                           = 3
CMD_CONFIG_PROLOGUE_FU               = 4
CMD_CONFIG_PROLOGUE_FU_CROSSBAR      = 5
CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR = 6
CMD_CONFIG_TOTAL_CTRL_COUNT          = 7
CMD_CONFIG_COUNT_PER_ITER            = 8
CMD_CONFIG_CTRL_UPPER_BOUND          = 9
CMD_CONFIG_CTRL_LOWER_BOUND          = 10
CMD_LOAD_REQUEST                     = 11
CMD_LOAD_RESPONSE                    = 12
CMD_STORE_REQUEST                    = 13
CMD_CONST                            = 14
CMD_COMPLETE                         = 15

CMD_SYMBOL_DICT = {
  CMD_LAUNCH:                           "(LAUNCH_KERNEL)",
  CMD_PAUSE:                            "(PAUSE_EXECUTION)",
  CMD_TERMINATE:                        "(TERMINATE_EXECUTION)",
  CMD_CONFIG:                           "(PRELOADING_KERNEL_CONFIG)",
  CMD_CONFIG_PROLOGUE_FU:               "(PRELOADING_PROLOGUE_FU)",
  CMD_CONFIG_PROLOGUE_FU_CROSSBAR:      "(PRELOADING_PROLOGUE_FU_CROSSBAR)",
  CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR: "(PRELOADING_PROLOGUE_ROUTING_CROSSBAR)",
  CMD_CONFIG_TOTAL_CTRL_COUNT:          "(PRELOAD_CONFIG_COUNT)",
  CMD_CONFIG_COUNT_PER_ITER:            "(PRELOAD_CONFIG_COUNT_PER_ITER)",
  CMD_CONFIG_CTRL_UPPER_BOUND:          "(READING_CONFIG_START_ADDR)",
  CMD_CONFIG_CTRL_LOWER_BOUND:          "(READING_CONFIG_END_ADDR)",
  CMD_LOAD_REQUEST:                     "(LOAD_REQUEST)",
  CMD_LOAD_RESPONSE:                    "(LOAD_RESPONSE)",
  CMD_STORE_REQUEST:                    "(STORE_REQUEST)",
  CMD_CONST:                            "(CONST_DATA)",
  CMD_COMPLETE:                         "(COMPLETE_EXECUTION)"
}

