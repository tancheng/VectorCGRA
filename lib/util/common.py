"""
=========================================================================
common.py
=========================================================================
Author : Cheng Tan
  Date : Dec 24, 2022
"""

# Constants for port index.
PORT_INDEX_NORTH     = 0
PORT_INDEX_SOUTH     = 1
PORT_INDEX_WEST      = 2
PORT_INDEX_EAST      = 3
PORT_INDEX_NORTHWEST = 4
PORT_INDEX_NORTHEAST = 5
PORT_INDEX_SOUTHEAST = 6
PORT_INDEX_SOUTHWEST = 7
PORT_INDEX_DIRECTION_COUNTS = 8

# Constants for routing directions.
PORT_NAH = 0
PORT_NORTH     = PORT_INDEX_NORTH + 1
PORT_SOUTH     = PORT_INDEX_SOUTH + 1
PORT_WEST      = PORT_INDEX_WEST + 1
PORT_EAST      = PORT_INDEX_EAST + 1
PORT_NORTHWEST = PORT_INDEX_NORTHWEST + 1
PORT_NORTHEAST = PORT_INDEX_NORTHEAST + 1
PORT_SOUTHEAST = PORT_INDEX_SOUTHEAST + 1
PORT_SOUTHWEST = PORT_INDEX_SOUTHWEST + 1

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

# Constant for number of inports on the controller xbar towards NoC.
# Crossbar with 6 inports (load and store requests towards remote
# memory, load response from local memory, ctrl&data packet from cpu,
# command signal from inter-tile, i.e., intra-cgra -- ring, and
# global reduce unit) and 1 outport (only allow one request be sent
# out per cycle).
CONTROLLER_CROSSBAR_INPORTS = 6

GLOBAL_REDUCE_MAX_COUNT = 4

# Cgra Topology
MESH = "Mesh"
KING_MESH = "KingMesh"
