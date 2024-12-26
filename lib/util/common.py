"""
=========================================================================
common.py
=========================================================================
Author : Cheng Tan
  Date : Dec 24, 2022
"""

# Constants for routing directions

PORT_NORTH     = 0
PORT_SOUTH     = 1
PORT_WEST      = 2
PORT_EAST      = 3
PORT_NORTHWEST = 4
PORT_NORTHEAST = 5
PORT_SOUTHEAST = 6
PORT_SOUTHWEST = 7
PORT_DIRECTION_COUNTS = 8

LINK_NO_MEM   = 0
LINK_FROM_MEM = 1
LINK_TO_MEM   = 2

TILE_PORT_DIRECTION_DICT = {
    PORT_NORTH: "NORTH",
    PORT_SOUTH: "SOUTH",
    PORT_WEST: "WEST",
    PORT_EAST: "EAST",
    PORT_NORTHWEST: "NORTHWEST",
    PORT_NORTHEAST: "NORTHEAST",
    PORT_SOUTHEAST: "SOUTHEAST",
    PORT_SOUTHWEST: "SOUTHWEST"
}

TILE_PORT_DIRECTION_DICT_SHORT_DESC = {
    PORT_NORTH: "N",
    PORT_SOUTH: "S",
    PORT_WEST: "W",
    PORT_EAST: "E",
    PORT_NORTHWEST: "NW",
    PORT_NORTHEAST: "NE",
    PORT_SOUTHEAST: "SE",
    PORT_SOUTHWEST: "SW"
}
