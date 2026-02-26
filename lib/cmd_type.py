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
NUM_CMDS = 43

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
CMD_UPDATE_COUNTER_SHADOW_VALUE      = 26  # Updates shadow registers value from AC.
CMD_RESET_LEAF_COUNTER               = 27  # Resets leaf counter to lower_bound.
CMD_CONFIG_LOOP_LOWER                = 28
CMD_CONFIG_LOOP_UPPER                = 29
CMD_CONFIG_LOOP_STEP                 = 30
CMD_LEAF_COUNTER_COMPLETE            = 31

# Affine Controller (AC) Configuration Commands (from CPU).
CMD_AC_CONFIG_LOWER                  = 32  # Configures CCU lower_bound.
CMD_AC_CONFIG_UPPER                  = 33  # Configures CCU upper_bound.
CMD_AC_CONFIG_STEP                   = 34  # Configures CCU step.
CMD_AC_CONFIG_CHILD_COUNT            = 35  # Configures child_complete_count.
CMD_AC_CONFIG_TARGET                 = 36  # Configures target (tile_id, ctrl_addr, is_remote, cgra_id).
CMD_AC_CONFIG_PARENT                 = 37  # Configures parent_ccu_id, is_root, is_relay.
CMD_AC_LAUNCH                        = 38  # Launches AC (all CCUs enter RUNNING).

# Affine Controller Inter-CGRA Sync Commands.
CMD_AC_SYNC_VALUE                    = 39  # Parent AC → Child AC: sync current value.
CMD_AC_CHILD_COMPLETE                = 40  # Child AC → Parent AC: child complete.
CMD_AC_CHILD_RESET                   = 41  # Parent AC → Child AC: reset child.

# Affine Controller Status.
CMD_AC_ALL_COMPLETE                  = 42  # AC → Controller: all loops complete.

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
  CMD_CONFIG_STREAMING_LD_END_ADDR:     "(STREAMING_LD_END_ADDR)",
  CMD_UPDATE_COUNTER_SHADOW_VALUE:      "(UPDATE_COUNTER_SHADOW_REGISTER)",
  CMD_RESET_LEAF_COUNTER:               "(RESET_LEAF_COUNTER)",
  CMD_CONFIG_LOOP_LOWER:                "(CONFIG_LOOP_LOWER)",
  CMD_CONFIG_LOOP_UPPER:                "(CONFIG_LOOP_UPPER)",
  CMD_CONFIG_LOOP_STEP:                 "(CONFIG_LOOP_STEP)",
  CMD_LEAF_COUNTER_COMPLETE:            "(LEAF_COUNTER_COMPLETE)",
  CMD_AC_CONFIG_LOWER:                  "(AC_CONFIG_CCU_LOWER)",
  CMD_AC_CONFIG_UPPER:                  "(AC_CONFIG_CCU_UPPER)",
  CMD_AC_CONFIG_STEP:                   "(AC_CONFIG_CCU_STEP)",
  CMD_AC_CONFIG_CHILD_COUNT:            "(AC_CONFIG_CCU_CHILD_COUNT)",
  CMD_AC_CONFIG_TARGET:                 "(AC_CONFIG_CCU_TARGET)",
  CMD_AC_CONFIG_PARENT:                 "(AC_CONFIG_CCU_PARENT)",
  CMD_AC_LAUNCH:                        "(AC_LAUNCH)",
  CMD_AC_SYNC_VALUE:                    "(AC_SYNC_VALUE)",
  CMD_AC_CHILD_COMPLETE:                "(AC_CHILD_COMPLETE)",
  CMD_AC_CHILD_RESET:                   "(AC_CHILD_RESET)",
  CMD_AC_ALL_COMPLETE:                  "(AC_ALL_COMPLETE)",
}

