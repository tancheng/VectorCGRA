"""
=========================================================================
common.py
=========================================================================
Author : Cheng Tan
  Date : Dec 24, 2022
"""

# Constants for routing directions.

PORT_NORTH     = 0
PORT_SOUTH     = 1
PORT_WEST      = 2
PORT_EAST      = 3
PORT_NORTHWEST = 4
PORT_NORTHEAST = 5
PORT_SOUTHEAST = 6
PORT_SOUTHWEST = 7
PORT_DIRECTION_COUNTS = 8

PORT_ROUTING_CROSSBAR = 0
PORT_FU_CROSSBAR = 1
PORT_CONST = 2

LINK_NO_MEM   = 0
LINK_FROM_MEM = 1
LINK_TO_MEM   = 2

# Constant for maximum control-message count.

MAX_CTRL_COUNT = 1024

# Constant for prologue max count.

PROLOGUE_MAX_COUNT = 7
