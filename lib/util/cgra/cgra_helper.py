from .Link import Link
from ..common import *

def get_links(tiles):
    """
    Get the links of tiles in one CGRA for a general RxC mesh.
                
    Mapping way of tiles in a single CGRA (Cartesian coordinate system):
        ^
        |   y (row) increases upward: 0 at the bottom, up to `per_cgra_rows-1` at the top
        |
        |   (row, col): (y, x)
        +------------------------>
        0                        x (column) increases to the right: 0 at the left, up to `per_cgra_columns-1` at the right  
    """
    per_cgra_row = len(tiles)
    per_cgra_col = len(tiles[0])
    links = []

    # --- 1. Memory Connections (West Side) ---
    # Creates bidirectional links between memory and each tile in the first column (col 0).
    # The memPort index is assumed to match the row index.
    for r in range(per_cgra_row):
        # From memory to tile
        link_from_mem = Link(None, tiles[r][0], r, PORT_INDEX_WEST)
        link_from_mem.fromMem = True
        # The leftmost column of tiles connects to ports [0, per_cgra_row - 1] of dataSPM.
        link_from_mem.memPort = r
        link_from_mem.validatePorts()
        links.append(link_from_mem)

        # From tile to memory
        link_to_mem = Link(tiles[r][0], None, PORT_INDEX_WEST, r)
        link_to_mem.toMem = True
        link_to_mem.memPort = r
        link_to_mem.validatePorts()
        links.append(link_to_mem)

    # --- Memory Connections (South Side) ---
    # Creates bidirectional links between memory and each tile in the bottom row.
    for c in range(1, per_cgra_col):
        # From memory to tile.
        link_from_mem = Link(None, tiles[0][c], per_cgra_row - 1 + c, PORT_INDEX_SOUTH)
        link_from_mem.fromMem = True
        # The bottom row of tiles connects to ports [per_cgra_row, per_cgra_row + per_cgra_col - 2]
        link_from_mem.memPort = per_cgra_row - 1 + c
        link_from_mem.validatePorts()
        links.append(link_from_mem)

        # From tile to memory.
        link_to_mem = Link(tiles[0][c], None, PORT_INDEX_SOUTH, per_cgra_row - 1 + c)
        link_to_mem.toMem = True
        link_to_mem.memPort = per_cgra_row - 1 + c
        link_to_mem.validatePorts()
        links.append(link_to_mem)

    # --- 2. Horizontal Connections (East-West) ---
    # Creates bidirectional links for all horizontally adjacent tiles.
    for r in range(per_cgra_row):
        for c in range(per_cgra_col - 1):
            # Eastward: (r, c) -> (r, c+1)
            link_east = Link(tiles[r][c], tiles[r][c+1], PORT_INDEX_EAST, PORT_INDEX_WEST)
            link_east.validatePorts()
            links.append(link_east)

            # Westward: (r, c+1) -> (r, c)
            link_west = Link(tiles[r][c+1], tiles[r][c], PORT_INDEX_WEST, PORT_INDEX_EAST)
            link_west.validatePorts()
            links.append(link_west)

    # --- 3. Vertical Connections (North-South) ---
    # Creates bidirectional links for all vertically adjacent tiles.
    # Note: Following the 2x2 pattern, (r,c).NORTH connects to (r+1,c).SOUTH
    for r in range(per_cgra_row - 1):
        for c in range(per_cgra_col):
            # "Downward" (North port -> South port)
            link_down = Link(tiles[r][c], tiles[r+1][c], PORT_INDEX_NORTH, PORT_INDEX_SOUTH)
            link_down.validatePorts()
            links.append(link_down)

            # "Upward" (South port -> North port)
            link_up = Link(tiles[r+1][c], tiles[r][c], PORT_INDEX_SOUTH, PORT_INDEX_NORTH)
            link_up.validatePorts()
            links.append(link_up)

    # --- 4. Diagonal Connections ---
    # Creates bidirectional links for all diagonally adjacent tiles.
    for r in range(per_cgra_row - 1):
        for c in range(per_cgra_col - 1):
            
            # NE <-> SW: (r, c) <-> (r+1, c+1)
            link_ne_sw = Link(tiles[r][c], tiles[r+1][c+1], PORT_INDEX_NORTHEAST, PORT_INDEX_SOUTHWEST)
            link_ne_sw.validatePorts()
            links.append(link_ne_sw)

            link_sw_ne = Link(tiles[r+1][c+1], tiles[r][c], PORT_INDEX_SOUTHWEST, PORT_INDEX_NORTHEAST)
            link_sw_ne.validatePorts()
            links.append(link_sw_ne)

            # NW <-> SE: (r, c+1) <-> (r+1, c)
            link_nw_se = Link(tiles[r][c+1], tiles[r+1][c], PORT_INDEX_NORTHWEST, PORT_INDEX_SOUTHEAST)
            link_nw_se.validatePorts()
            links.append(link_nw_se)

            link_se_nw = Link(tiles[r+1][c], tiles[r][c+1], PORT_INDEX_SOUTHEAST, PORT_INDEX_NORTHWEST)
            link_se_nw.validatePorts()
            links.append(link_se_nw)

    return links



def set_port_validity(tile, port, is_valid = True):
    """
    Modifies the validity of a port on a tile.

    Parameters:
    - tile: A tile object.
    - port: The port ID(PORT_INDEX_EAST, PORT_INDEX_WEST, PORT_INDEX_SOUTH, PORT_INDEX_NORTH).
    - is_valid: If True, enables the port(removes from invalid sets), otherwise 
      disables the port(adds to the invalid sets).
    """
    # Get the sets of invalid out and in ports of the tile.
    target_sets = [tile.invalidOutPorts, tile.invalidInPorts]

    for port_set in target_sets:
        if is_valid:
            port_set.discard(port)
        else:
            port_set.add(port)


def configure_boundary_ports(cgra_id, tiles_flat,
                                num_cgra_rows, num_cgra_cols,
                                id2shape_map,
                                is_valid = True):
    """
    Enable boundary ports for tiles on adjacent CGRAs.

    Parameters:
    - cgra_id: ID of the current CGRA (0-indexed, bottom-left to top-right)
    - tiles_flat: Flat list of tiles for this CGRA (reshaped from 2D)
    - num_cgra_rows: Number of CGRA rows in the mesh
    - num_cgra_cols: Number of CGRA columns in the mesh
    - id2shape_map: Map of each CGRA id to its shape: (num_tile_rows x num_tile_columns) tiles
    - is_valid: If true, enable ports, otherwise disable ports
    """
    # Converts CGRA ID to 2D coordinates
    cgra_x = cgra_id % num_cgra_cols
    cgra_y = cgra_id // num_cgra_cols
    # The number of tile rows and columns in the current CGRA.
    num_tile_rows, num_tile_cols = id2shape_map[cgra_id]

    # Helper to get tile from flat list using x/y indices
    def get_tile(x, y):
        return tiles_flat[y * num_tile_cols + x]

    # Enables NORTH ports if there's a neighbor to the north
    if cgra_y < num_cgra_rows - 1:
        # This CGRA has a neighbor above
        # Gets the tile shape of the neighbor CGRA.
        neighbor_cgra_id = cgra_id + num_cgra_cols
        num_neighbor_tile_rows, num_neighbor_tile_cols = id2shape_map[neighbor_cgra_id]

        # Top row of tiles in this CGRA should have NORTH ports enabled
        # y axis of the top row tiles of the current CGRA.
        top_row_y = num_tile_rows - 1
        valid_port_num = min(num_tile_cols, num_neighbor_tile_cols)
        for tile_x in range(valid_port_num):
            set_port_validity(get_tile(tile_x, top_row_y), PORT_INDEX_NORTH, is_valid)

    # Enables SOUTH ports if there's a neighbor to the south
    if cgra_y > 0:
        # This CGRA has a neighbor below
        # Gets the tile shape of the neighbor CGRA.
        neighbor_cgra_id = cgra_id - num_cgra_cols
        num_neighbor_tile_rows, num_neighbor_tile_cols = id2shape_map[neighbor_cgra_id]

        # Bottom row of tiles in this CGRA should have SOUTH ports enabled
        bottom_row_y = 0
        valid_port_num = min(num_tile_cols, num_neighbor_tile_cols)
        for tile_x in range(valid_port_num):
            set_port_validity(get_tile(tile_x, bottom_row_y), PORT_INDEX_SOUTH, is_valid)

    # Enables EAST ports if there's a neighbor to the east
    if cgra_x < num_cgra_cols - 1:
        # This CGRA has a neighbor to the right.
        # Gets the tile shape of the neighbor CGRA.
        neighbor_cgra_id = cgra_id + 1
        num_neighbor_tile_rows, num_neighbor_tile_cols = id2shape_map[neighbor_cgra_id]

        # Rightmost column of tiles in this CGRA should have EAST ports enabled
        east_col_x = num_tile_cols - 1
        valid_port_num = min(num_tile_rows, num_neighbor_tile_rows)
        for tile_y in range(valid_port_num):
            set_port_validity(get_tile(east_col_x, tile_y), PORT_INDEX_EAST, is_valid)

    # Enables WEST ports if there's a neighbor to the west
    if cgra_x > 0:
        # This CGRA has a neighbor to the left.
        # Gets the tile shape of the neighbor CGRA.
        neighbor_cgra_id = cgra_id - 1
        num_neighbor_tile_rows, num_neighbor_tile_cols = id2shape_map[neighbor_cgra_id]

        # Leftmost column of tiles in this CGRA should have WEST ports enabled
        west_col_x = 0
        valid_port_num = min(num_tile_rows, num_neighbor_tile_rows)
        for tile_y in range(valid_port_num):
            set_port_validity(get_tile(west_col_x, tile_y), PORT_INDEX_WEST, is_valid)
