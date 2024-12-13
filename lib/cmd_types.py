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

CMD_LAUNCH = Bits6(0)
CMD_PAUSE = Bits6(1)
CMD_TERMINATE = Bits6(2)
CMD_CONFIG = Bits6(3)
CMD_LOAD = Bits6(4)
CMD_STORE = Bits6(5)

CMD_SYMBOL_DICT = {
  CMD_LAUNCH: "(LAUNCH_KERNEL)",
  CMD_PAUSE: "(PAUSE_EXECUTION)",
  CMD_TERMINATE: "(TERMINATE_EXECUTION)",
  CMD_CONFIG: "(PRELOADING_KERNEL_CONFIG)",
  CMD_LOAD: "(LOAD_DATA)",
  CMD_STORE: "(STORE_DATA)",
}
