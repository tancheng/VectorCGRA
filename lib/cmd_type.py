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
NUM_CMDS = 22

CMD_LAUNCH                           = 0
CMD_PAUSE                            = 1
CMD_TERMINATE                        = 2
CMD_CONFIG                           = 3
CMD_CONFIG_PROLOGUE_FU               = 4
CMD_CONFIG_PROLOGUE_FU_CROSSBAR      = 5
CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR = 6
CMD_CONFIG_TOTAL_CTRL_COUNT          = 7
CMD_CONFIG_COUNT_PER_ITER            = 8
CMD_CONFIG_CTRL_LOWER_BOUND          = 9
CMD_LOAD_REQUEST                     = 10
CMD_LOAD_RESPONSE                    = 11
CMD_STORE_REQUEST                    = 12
CMD_CONST                            = 13
CMD_COMPLETE                         = 14
CMD_RESUME                           = 15
CMD_RECORD_INIT_PHI_ADDR             = 16
CMD_GLOBAL_REDUCE_COUNT              = 17
CMD_GLOBAL_REDUCE_ADD                = 18
CMD_GLOBAL_REDUCE_MUL                = 19
CMD_GLOBAL_REDUCE_ADD_RESPONSE       = 20
CMD_GLOBAL_REDUCE_MUL_RESPONSE       = 21

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
  CMD_CONFIG_CTRL_LOWER_BOUND:          "(PRELOAD_CONFIG_LOWER_ADDR)",
  CMD_LOAD_REQUEST:                     "(LOAD_REQUEST)",
  CMD_LOAD_RESPONSE:                    "(LOAD_RESPONSE)",
  CMD_STORE_REQUEST:                    "(STORE_REQUEST)",
  CMD_CONST:                            "(CONST_DATA)",
  CMD_COMPLETE:                         "(COMPLETE_EXECUTION)",
  CMD_RESUME:                           "(RESUME_EXECUTION)",
  CMD_RECORD_INIT_PHI_ADDR:             "(RECORD_INIT_PHI_ADDR)",
  CMD_GLOBAL_REDUCE_COUNT:              "(GLOBAL_REDUCE_COUNT)",
  CMD_GLOBAL_REDUCE_ADD:                "(GLOBAL_REDUCE_ADD)",
  CMD_GLOBAL_REDUCE_MUL:                "(GLOBAL_REDUCE_MUL)",
  CMD_GLOBAL_REDUCE_ADD_RESPONSE:       "(GLOBAL_REDUCE_ADD_RESPONSE)",
  CMD_GLOBAL_REDUCE_MUL_RESPONSE:       "(GLOBAL_REDUCE_MUL_RESPONSE)"
}

