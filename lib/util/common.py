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

PORT_INDEX_ROUTING_CROSSBAR = 0
PORT_INDEX_FU_CROSSBAR = 1
PORT_INDEX_CONST = 2

PORT_ROUTING_CROSSBAR = PORT_INDEX_ROUTING_CROSSBAR + 1
PORT_FU_CROSSBAR = PORT_INDEX_FU_CROSSBAR + 1
PORT_CONST = PORT_INDEX_CONST + 1

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

# Register cluster read direction enums
READ_TOWARDS_NOTHING      = 0
READ_TOWARDS_FU           = 1
READ_TOWARDS_ROUTING_XBAR = 2
READ_TOWARDS_BOTH         = 3

############################
# Constants for DMA engine.
############################
# DMA Move In and Out
# DMA_MVIN  : DRAM -> DMA Engine -> SPM
# DMA_MVOUT : SPM -> DMA Engine -> DRAM
DMA_MVIN  = 0
DMA_MVOUT = 1

# 1 byte = 8 bits
CHAR_BIT = 8

# State machine definitions of DMA engine.
from pymtl3 import mk_bits
StateType = mk_bits( 4 )
STATE_DMA_IDLE          = StateType( 0 ) # Waiting for a new DMA command
STATE_DMA_MVIN_REQ      = StateType( 1 ) # MVIN: Issuing DRAM read request
STATE_DMA_MVIN_RESP     = StateType( 2 ) # MVIN: Waiting for DRAM read response
STATE_DMA_MVIN_WRITE    = StateType( 3 ) # MVIN: Writing unpacked words to SPM
STATE_DMA_MVOUT_READ    = StateType( 4 ) # MVOUT: Issuing SPM read request
STATE_DMA_MVOUT_RESP    = StateType( 5 ) # MVOUT: Receiving SPM read response and packing
STATE_DMA_MVOUT_WRITE   = StateType( 6 ) # MVOUT: Issuing DRAM write request
STATE_DMA_MVOUT_WAIT    = StateType( 7 ) # MVOUT: Waiting for DRAM write response
STATE_DMA_DONE          = StateType( 8 ) # Signaling command completion
