from .Link import Link
from ..common import *

def get_links(tiles):
    """
    Get the links of tiles in one CGRA for a general RxC mesh.
    """
    per_cgra_row = len(tiles)
    per_cgra_col = len(tiles[0])
    links = []

    # --- 1. Memory Connections (West Side) ---
    # Creates bidirectional links between memory and each tile in the first column (col 0).
    # The memPort index is assumed to match the row index.
    for r in range(per_cgra_row):
        # From memory to tile
        link_from_mem = Link(None, tiles[r][0], r, PORT_WEST)
        link_from_mem.fromMem = True
        link_from_mem.memPort = r
        link_from_mem.validatePorts()
        links.append(link_from_mem)

        # From tile to memory
        link_to_mem = Link(tiles[r][0], None, PORT_WEST, r)
        link_to_mem.toMem = True
        link_to_mem.memPort = r
        link_to_mem.validatePorts()
        links.append(link_to_mem)

    # --- 2. Horizontal Connections (East-West) ---
    # Creates bidirectional links for all horizontally adjacent tiles.
    for r in range(per_cgra_row):
        for c in range(per_cgra_col - 1):
            # Eastward: (r, c) -> (r, c+1)
            link_east = Link(tiles[r][c], tiles[r][c+1], PORT_EAST, PORT_WEST)
            link_east.validatePorts()
            links.append(link_east)

            # Westward: (r, c+1) -> (r, c)
            link_west = Link(tiles[r][c+1], tiles[r][c], PORT_WEST, PORT_EAST)
            link_west.validatePorts()
            links.append(link_west)

    # --- 3. Vertical Connections (North-South) ---
    # Creates bidirectional links for all vertically adjacent tiles.
    # Note: Following the 2x2 pattern, (r,c).NORTH connects to (r+1,c).SOUTH
    for r in range(per_cgra_row - 1):
        for c in range(per_cgra_col):
            # "Downward" (North port -> South port)
            link_down = Link(tiles[r][c], tiles[r+1][c], PORT_NORTH, PORT_SOUTH)
            link_down.validatePorts()
            links.append(link_down)

            # "Upward" (South port -> North port)
            link_up = Link(tiles[r+1][c], tiles[r][c], PORT_SOUTH, PORT_NORTH)
            link_up.validatePorts()
            links.append(link_up)

    # --- 4. Diagonal Connections ---
    # Creates bidirectional links for all diagonally adjacent tiles.
    for r in range(per_cgra_row - 1):
        for c in range(per_cgra_col - 1):
            
            # NE <-> SW: (r, c) <-> (r+1, c+1)
            link_ne_sw = Link(tiles[r][c], tiles[r+1][c+1], PORT_NORTHEAST, PORT_SOUTHWEST)
            link_ne_sw.validatePorts()
            links.append(link_ne_sw)

            link_sw_ne = Link(tiles[r+1][c+1], tiles[r][c], PORT_SOUTHWEST, PORT_NORTHEAST)
            link_sw_ne.validatePorts()
            links.append(link_sw_ne)

            # NW <-> SE: (r, c+1) <-> (r+1, c)
            link_nw_se = Link(tiles[r][c+1], tiles[r+1][c], PORT_NORTHWEST, PORT_SOUTHEAST)
            link_nw_se.validatePorts()
            links.append(link_nw_se)

            link_se_nw = Link(tiles[r+1][c], tiles[r][c+1], PORT_SOUTHEAST, PORT_NORTHWEST)
            link_se_nw.validatePorts()
            links.append(link_se_nw)

    return links



def keep_port_valid(tile, port):
    """
    Removes the given port from the sets of invalid out and in ports of the tile.

    Parameters:
    - tile: A tile object.
    - port: An integer representing the port to be made valid.
    """
    # Get the sets of invalid out and in ports of the tile.
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
