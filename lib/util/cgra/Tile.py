from ..common import PORT_DIRECTION_COUNTS


operation2FuType = {
    # Phi Unit
    "phi": "Phi",
    # Add/Sub Unit
    "add": "Add", "sub": "Add", "fadd": "Add", "fsub": "Add", "fadd_fadd": "Add",
    # Shift Unit
    "shl": "Shift",
    # Load Unit
    "load": "Ld",
    # Select Unit
    "sel": "Sel",
    # Compare Unit
    "icmp": "Cmp", "fcmp": "Cmp",
    # MAC Unit
    "fmul_fadd": "MAC",
    # Store Unit
    "store": "St",
    # Return Unit
    "ret": "Ret",
    # Multiply/Divide/Remainder Unit
    "mul": "Mul", "fmul": "Mul", "vfmul": "Mul", "div": "Mul", "rem": "Mul", "fdiv": "Mul",
    # Logic/Conversion/Data Movement Unit
    "or": "Logic", "not": "Logic", "cast": "Logic", "sext": "Logic", "zext": "Logic", 
    "data_mov": "Logic", "ctrl_mov": "Logic",
    # Grant Unit
    "grant_predicate": "Grant", "grant_once": "Grant", "grant_always": "Grant",
    # Loop Control Unit
    "loop_control": "Loop_Control",
    # Constant Unit
    "constant": "Constant",
}

class Tile:
    """
    Represents a single tile in the CGRA array configuration.
    This class holds the static configuration parameters for a tile, including its location,
    functional units (operations), and connectivity status (memory access, valid ports).
    It is used during the parameterization phase to configure the RTL generation.
    """

    def __init__(self, dimX, dimY, num_registers, operations):
        self.disabled = False
        self.dimX = dimX  # Column index (X coordinate) in the CGRA mesh
        self.dimY = dimY  # Row index (Y coordinate) in the CGRA mesh
        # Number of registers in the tile's register file
        self.num_registers = num_registers
        self.operations = operations
        self.isDefaultFus_ = True  # Flag indicating if the tile uses the default set of FUs

        # toMem: Indicates if this tile has a dedicated link TO the data memory (for Store operations).
        self.toMem = False

        # fromMem: Indicates if this tile has a dedicated link FROM the data memory (for Load operations).
        self.fromMem = False

        # invalidOutPorts: A set containing port indices (e.g., PORT_NORTH, PORT_EAST) that are NOT used
        # as output ports. Initialized to contain ALL ports. When a link is created originating from this
        # tile, the corresponding port is removed from this set.
        # Used in RTL generation to ground/disable unused output ports.
        self.invalidOutPorts = set()

        # invalidInPorts: A set containing port indices that are NOT used as input ports.
        # Initialized to contain ALL ports. When a link is created terminating at this tile,
        # the corresponding port is removed from this set.
        # Used in RTL generation to ground/disable unused input ports.
        self.invalidInPorts = set()

        for i in range(PORT_DIRECTION_COUNTS):
            self.invalidOutPorts.add(i)
            self.invalidInPorts.add(i)

    def getInvalidInPorts(self):
        """Returns the set of unused input ports."""
        return self.invalidInPorts

    def getInvalidOutPorts(self):
        """Returns the set of unused output ports."""
        return self.invalidOutPorts

    def hasToMem(self):
        """Returns True if the tile connects to memory (write/store)."""
        return self.toMem

    def hasFromMem(self):
        """Returns True if the tile receives from memory (read/load)."""
        return self.fromMem

    def getIndex(self, TileList):
        """
        Calculates the flattened index of this tile within a given list of tiles.
        This is used to map the logical Tile object to the physical TileRTL instance index
        in the top-level CGRA component.

        Args:
            TileList: A list of all Tile objects in the CGRA.

        Returns:
            int: The 0-based index of this tile, skipping disabled tiles. 
                 Returns -1 if this tile is disabled.
        """
        if self.disabled:
            return -1
        index = 0
        for tile in TileList:
            # Counts valid tiles that appear before 's' in row-major order (Row Y, then Col X)
            if tile.dimY < self.dimY and not tile.disabled:
                index += 1
            elif tile.dimY == self.dimY and tile.dimX < self.dimX and not tile.disabled:
                index += 1
        return index

    def isDefaultFus(self):
        return self.isDefaultFus_

    def getAllValidFuTypes(self):
        required_fu_set = set()
        for op in self.operations:
            try:
                fu_type = operation2FuType[op]
                required_fu_set.add(fu_type)
            except KeyError:
                # Handle cases where an operation is not defined in the map
                print(f"Warning: Operation '{op}' is not defined in operation2FuType map.")
        
        return list(required_fu_set)

    def override(self, operations, existence):
        """
        Overrides the default configuration for this tile.

        Args:
            operations: New list of supported operations.
            existence: Boolean, if False, marks the tile as disabled (not physically present/active).
        """
        self.operations = operations
        self.disabled = not existence
        self.isDefaultFus_ = False
