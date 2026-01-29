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
NUM_CMDS = 28

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
CMD_RECORD_PHI_ADDR                  = 16
CMD_GLOBAL_REDUCE_COUNT              = 17
CMD_GLOBAL_REDUCE_ADD                = 18
CMD_GLOBAL_REDUCE_MUL                = 19
CMD_GLOBAL_REDUCE_ADD_RESPONSE       = 20
CMD_GLOBAL_REDUCE_MUL_RESPONSE       = 21
CMD_PRESERVE                         = 22
CMD_CONFIG_STREAMING_LD_START_ADDR   = 23
CMD_CONFIG_STREAMING_LD_STRIDE       = 24
CMD_CONFIG_STREAMING_LD_END_ADDR     = 25
CMD_UPDATE_COUNTER_SHADOW_VALUE      = 23  # Updates shadow registers value from AC.
CMD_RESET_LEAF_COUNTER               = 24  # Resets leaf counter to lower_bound.
CMD_CONFIG_LOOP_LOWER                = 25
CMD_CONFIG_LOOP_UPPER                = 26
CMD_CONFIG_LOOP_STEP                 = 27
CMD_LEAF_COUNTER_COMPLETE            = 28

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
  CMD_RECORD_PHI_ADDR:                  "(RECORD_TARGET_PHI_CONST_CTRL_MEM_ADDR)",
  CMD_GLOBAL_REDUCE_COUNT:              "(GLOBAL_REDUCE_COUNT)",
  CMD_GLOBAL_REDUCE_ADD:                "(GLOBAL_REDUCE_ADD)",
  CMD_GLOBAL_REDUCE_MUL:                "(GLOBAL_REDUCE_MUL)",
  CMD_GLOBAL_REDUCE_ADD_RESPONSE:       "(GLOBAL_REDUCE_ADD_RESPONSE)",
  CMD_GLOBAL_REDUCE_MUL_RESPONSE:       "(GLOBAL_REDUCE_MUL_RESPONSE)",
  CMD_PRESERVE:                         "(PRESERVE_ACCUMULATED_VALUE)",
  CMD_CONFIG_STREAMING_LD_START_ADDR:   "(STREAMING_LD_START_ADDR)",
  CMD_CONFIG_STREAMING_LD_STRIDE:       "(STREAMING_LD_STRIDE)",
  CMD_CONFIG_STREAMING_LD_END_ADDR:     "(STREAMING_LD_END_ADDR)"
  CMD_UPDATE_COUNTER_SHADOW_VALUE:      "(UPDATE_COUNTER_SHADOW_REGISTER)",
  CMD_RESET_LEAF_COUNTER:               "(RESET_LEAF_COUNTER)",
  CMD_CONFIG_LOOP_LOWER:                "(CONFIG_LOOP_LOWER)",
  CMD_CONFIG_LOOP_UPPER:                "(CONFIG_LOOP_UPPER)",
  CMD_CONFIG_LOOP_STEP:                 "(CONFIG_LOOP_STEP)",
  CMD_LEAF_COUNTER_COMPLETE:            "(LEAF_COUNTER_COMPLETE)",
}

