from .Link import Link
from ...lib.util.common import *


def get_links_2x2(tiles):
    """
    Get the links for a 2x2 tiles in one CGRA.
    """
    # TODO(@benkangpeng) May needs a bigger/more general links.
    links = [Link(None, None, 0, 0) for _ in range(16)]

    links[0].srcTile = None
    links[0].dstTile = tiles[0][0]
    links[0].srcPort = 0
    links[0].dstPort = PORT_WEST
    links[0].fromMem = True
    links[0].memPort = 0
    links[0].validatePorts()

    links[1].srcTile = tiles[0][0]
    links[1].dstTile = None
    links[1].srcPort = PORT_WEST
    links[1].dstPort = 0
    links[1].toMem = True
    links[1].memPort = 0
    links[1].validatePorts()

    links[2].srcTile = None
    links[2].dstTile = tiles[1][0]
    links[2].srcPort = 1
    links[2].dstPort = PORT_WEST
    links[2].fromMem = True
    links[2].memPort = 1
    links[2].validatePorts()

    links[3].srcTile = tiles[1][0]
    links[3].dstTile = None
    links[3].srcPort = PORT_WEST
    links[3].dstPort = 1
    links[3].toMem = True
    links[3].memPort = 1
    links[3].validatePorts()

    links[4].srcTile = tiles[0][0]
    links[4].dstTile = tiles[0][1]
    links[4].srcPort = PORT_EAST
    links[4].dstPort = PORT_WEST
    links[4].validatePorts()

    links[5].srcTile = tiles[0][1]
    links[5].dstTile = tiles[0][0]
    links[5].srcPort = PORT_WEST
    links[5].dstPort = PORT_EAST
    links[5].validatePorts()

    links[6].srcTile = tiles[1][0]
    links[6].dstTile = tiles[1][1]
    links[6].srcPort = PORT_EAST
    links[6].dstPort = PORT_WEST
    links[6].validatePorts()

    links[7].srcTile = tiles[1][1]
    links[7].dstTile = tiles[1][0]
    links[7].srcPort = PORT_WEST
    links[7].dstPort = PORT_EAST
    links[7].validatePorts()

    links[8].srcTile = tiles[0][0]
    links[8].dstTile = tiles[1][0]
    links[8].srcPort = PORT_NORTH
    links[8].dstPort = PORT_SOUTH
    links[8].validatePorts()

    links[9].srcTile = tiles[1][0]
    links[9].dstTile = tiles[0][0]
    links[9].srcPort = PORT_SOUTH
    links[9].dstPort = PORT_NORTH
    links[9].validatePorts()

    links[10].srcTile = tiles[0][1]
    links[10].dstTile = tiles[1][1]
    links[10].srcPort = PORT_NORTH
    links[10].dstPort = PORT_SOUTH
    links[10].validatePorts()

    links[11].srcTile = tiles[1][1]
    links[11].dstTile = tiles[0][1]
    links[11].srcPort = PORT_SOUTH
    links[11].dstPort = PORT_NORTH
    links[11].validatePorts()

    links[12].srcTile = tiles[0][0]
    links[12].dstTile = tiles[1][1]
    links[12].srcPort = PORT_NORTHEAST
    links[12].dstPort = PORT_SOUTHWEST
    links[12].validatePorts()

    links[13].srcTile = tiles[1][1]
    links[13].dstTile = tiles[0][0]
    links[13].srcPort = PORT_SOUTHWEST
    links[13].dstPort = PORT_NORTHEAST
    links[13].validatePorts()

    links[14].srcTile = tiles[0][1]
    links[14].dstTile = tiles[1][0]
    links[14].srcPort = PORT_NORTHWEST
    links[14].dstPort = PORT_SOUTHEAST
    links[14].validatePorts()

    links[15].srcTile = tiles[1][0]
    links[15].dstTile = tiles[0][1]
    links[15].srcPort = PORT_SOUTHEAST
    links[15].dstPort = PORT_NORTHWEST
    links[15].validatePorts()

    return links


def keep_port_valid(tile, port):
    tile_out_port_set = tile.invalidOutPorts
    tile_in_port_set = tile.invalidInPorts
    if port in tile_out_port_set:
        tile_out_port_set.remove(port)
    if port in tile_in_port_set:
        tile_in_port_set.remove(port)


def keep_port_valid_on_boundary(cgra_id, tiles_flat,
                                num_cgra_rows, num_cgra_columns,
                                per_cgra_rows, per_cgra_columns):
    """
    Enable boundary ports for tiles on adjacent CGRAs.

    Parameters:
    - cgra_id: ID of the current CGRA (0-indexed, bottom-left to top-right)
    - tiles_flat: Flat list of tiles for this CGRA (reshaped from 2D)
    - num_cgra_rows: Number of CGRA rows in the mesh
    - num_cgra_columns: Number of CGRA columns in the mesh
    - per_cgra_rows: Number of tile rows in each CGRA
    - per_cgra_columns: Number of tile columns in each CGRA

    CGRA ID mapping (example for 2x2):
    CGRA 2: [row=0, col=0] CGRA 3: [row=0, col=1]  (top row, row=0)
    CGRA 0: [row=1, col=0] CGRA 1: [row=1, col=1]  (bottom row, row=1)
    """
    # Converts CGRA ID to 2D coordinates
    cgra_row = (num_cgra_rows - 1) - (cgra_id // num_cgra_columns)
    cgra_col = cgra_id % num_cgra_columns

    # Helper to get tile from flat list using row/col indices
    def get_tile(row, col):
        return tiles_flat[row * per_cgra_columns + col]

    # Enables NORTH ports if there's a neighbor to the north
    if cgra_row > 0:
        # This CGRA has a neighbor above
        # Top row of tiles in this CGRA should have NORTH ports enabled
        top_row_idx = per_cgra_rows - 1
        for tile_col in range(per_cgra_columns):
            keep_port_valid(get_tile(top_row_idx, tile_col), PORT_NORTH)

    # Enables SOUTH ports if there's a neighbor to the south
    if cgra_row < num_cgra_rows - 1:
        # This CGRA has a neighbor below
        # Bottom row of tiles in this CGRA should have SOUTH ports enabled
        bottom_row_idx = 0
        for tile_col in range(per_cgra_columns):
            keep_port_valid(get_tile(bottom_row_idx, tile_col), PORT_SOUTH)

    # Enables EAST ports if there's a neighbor to the east
    if cgra_col < num_cgra_columns - 1:
        # Rightmost column of tiles in this CGRA should have EAST ports enabled
        east_col_idx = per_cgra_columns - 1
        for tile_row in range(per_cgra_rows):
            keep_port_valid(get_tile(tile_row, east_col_idx), PORT_EAST)

    # Enables WEST ports if there's a neighbor to the west
    if cgra_col > 0:
        # Leftmost column of tiles in this CGRA should have WEST ports enabled
        west_col_idx = 0
        for tile_row in range(per_cgra_rows):
            keep_port_valid(get_tile(tile_row, west_col_idx), PORT_WEST)
