import yaml
from .MultiCgraParam import MultiCgraParam
from ...lib.util.cgra.DataSPM import DataSPM
from ...lib.util.cgra.Tile import Tile
from .ParamCGRA import ParamCGRA
from ...lib.util.cgra.cgra_helper import *
import copy


class ArchParser:
    def __init__(self, yaml_file: str):
        with open(yaml_file, "r") as f:
            self.yaml_data = yaml.safe_load(f)

        self.cgra_rows = self.yaml_data["multi_cgra_defaults"]["rows"]
        self.cgra_columns = self.yaml_data["multi_cgra_defaults"]["columns"]
        self.per_cgra_rows = self.yaml_data["cgra_defaults"]["rows"]
        self.per_cgra_columns = self.yaml_data["cgra_defaults"]["columns"]
        self.num_registers = self.yaml_data["tile_defaults"]["num_registers"]
        self.fu_types = self.yaml_data["tile_defaults"]["fu_types"]
        self.num_cgras = self.cgra_rows * self.cgra_columns
        # map of cgra_id to its shape: (per_cgra_rows, per_cgra_columns)
        self.id2shape_map = None

    def parse_dataSPM(self) -> dict[int, DataSPM]:
        if self.id2shape_map is None:
            raise ValueError("id2shape_map is not parsed yet.")
        id2dataSPM = {}
        for id in range(self.num_cgras):
            per_cgra_rows, per_cgra_columns = self.id2shape_map[id]
            data_mem_num_rd_tiles = per_cgra_rows + per_cgra_columns - 1
            data_mem_num_wr_tiles = per_cgra_rows + per_cgra_columns - 1
            id2dataSPM[id] = DataSPM(data_mem_num_rd_tiles, data_mem_num_wr_tiles)
        return id2dataSPM

    def parse_tiles(self):
        """
        Parse the tiles in one CGRA.
        We should consider the case of heterogeneous CGRA.
        """
        # map of cgra_id to tiles.
        id2tiles_map = {i: [] for i in range(self.num_cgras)}
        # default tiles.
        for i in range(self.num_cgras):
            """
            Mapping way of tiles in a single CGRA (Cartesian coordinate system):
            ^
            |   y increases upward: 0 at the bottom, up to `tile_row_num-1` at the top
            |
            |   (x,y)
            +------------------------>
            0                        x increases to the right: 0 at the left, up to `tile_column_num-1` at the right

            CGRA i
            ^
            |   tile6    tile7    tile8
            |   tile3    tile4    tile5
            |   tile0    tile1    tile2
            +------------------------>
            id2tiles_map[i] = [[tile0, tile1, tile2], [tile3, tile4, tile5], [tile6, tile7, tile8]]
            """
            for y in range(self.per_cgra_rows):
                id2tiles_map[i].append([])
                for x in range(self.per_cgra_columns):
                    id2tiles_map[i][y].append(
                        Tile(x, y, self.num_registers, self.fu_types)
                    )

        if "cgra_overrides" in self.yaml_data:
            for override in self.yaml_data["cgra_overrides"]:
                cgra_id = (
                    override["cgra_y"] * self.cgra_columns + override["cgra_x"]
                )
                override_tiles = []
                for y in range(override["rows"]):
                    override_tiles.append([])
                    for x in range(override["columns"]):
                        """
                        Mapping way of tiles in a single CGRA (Cartesian coordinate system):
                        ^
                        |   y increases upward: 0 at the bottom, up to `override["rows"]-1` at the top
                        |
                        |   (x,y)
                        +------------------------>
                        0                        x increases to the right: 0 at the left, up to `override["columns"]-1` at the right
                        """
                        override_tiles[y].append(
                            Tile(x, y, self.num_registers, self.fu_types)
                        )
                id2tiles_map[cgra_id] = override_tiles

        return id2tiles_map

    def parse_cgras(self):
        # Restricted by ControllerRTL.
        assert (
            self.cgra_rows <= self.cgra_columns
        ), "cgra_rows must be less than or equal to cgra_columns."
        # Restricted by data_mem_size_global(the power of 2).
        assert (self.num_cgras & (self.num_cgras - 1)) == 0, "num_cgras must be the power of 2."
        # cgra id to tiles map.
        id2tiles_map = self.parse_tiles()
        # Map of each CGRA id to its shape: (per_cgra_rows, per_cgra_columns)
        id2shape_map = {
            cgra_id: (len(id2tiles_map[cgra_id]), len(id2tiles_map[cgra_id][0]))
            for cgra_id in range(self.num_cgras)
        }
        self.id2shape_map = id2shape_map

        # cgra id to valid links.
        id2validLinks = {}
        # cgra id to valid tiles.
        id2validTiles = {}

        for id in range(self.num_cgras):
            tiles0 = copy.deepcopy(id2tiles_map[id])
            links0 = get_links(tiles0)
            # Flattens the tiles to a 1D list from left to right.
            # e.g., [[tile0, tile1], [tile2, tile3]] -> [tile0, tile1, tile2, tile3]
            tiles0_flat = [t for row in tiles0 for t in row]

            id2validLinks[id] = links0
            id2validTiles[id] = tiles0_flat

        # Iterates id2validTiles to enable boundary ports
        for cgra_id, tiles_flat in id2validTiles.items():
            configure_boundary_ports(
                cgra_id,
                tiles_flat,
                self.cgra_rows,
                self.cgra_columns,
                id2shape_map,
            )

        id2dataSPM = self.parse_dataSPM()
        ctrlMemSize = self.yaml_data["cgra_defaults"]["configMemSize"]
        id2ctrlMemSize_map = {id: ctrlMemSize for id in range(self.num_cgras)}

        cgras = []
        for y in range(self.cgra_rows):
            cgras.append([])
            for x in range(self.cgra_columns):
                id = y * self.cgra_columns + x
                cgras[y].append(
                    ParamCGRA(
                        id2shape_map[id][0],
                        id2shape_map[id][1],
                        id2validTiles[id],
                        id2validLinks[id],
                        id2dataSPM[id],
                        id2ctrlMemSize_map[id],
                    )
                )

        # Overrides the tiles.
        if "tile_overrides" in self.yaml_data:
            data = self.yaml_data["tile_overrides"]
            for override in data:
                fu_types = [] if not override["existence"] else override["fu_types"]
                cgras[override["cgra_y"]][override["cgra_x"]].overrideTiles(
                    override["tile_x"],
                    override["tile_y"],
                    fu_types,
                    override["existence"],
                )

        # Overrides the links.
        if "link_overrides" in self.yaml_data:
            data = self.yaml_data["link_overrides"]
            for override in data:
                if (
                    override["src_cgra_x"] == override["dst_cgra_x"]
                    and override["src_cgra_y"] == override["dst_cgra_y"]
                ):
                    cgras[override["src_cgra_y"]][override["src_cgra_x"]].overrideLinks(
                        override["src_tile_x"],
                        override["src_tile_y"],
                        override["dst_tile_x"],
                        override["dst_tile_y"],
                        override["existence"],
                    )
        return cgras

    def parse_multi_cgra_param(self):
        cgras = self.parse_cgras()
        return MultiCgraParam(self.cgra_rows, self.cgra_columns, cgras)

    def get_simplest_cgra_param(self) -> ParamCGRA:
        """
        Returns the simplest(has the least number of tiles) CGRA parameter.
        """
        cgras = self.parse_cgras()
        # set of (cgra_id, cgra)
        cgras_item = (
            (y * self.cgra_columns + x, cgras[y][x])
            for y in range(self.cgra_rows)
            for x in range(self.cgra_columns)
        )
        # Finds the cgra which has the least number of tiles.
        cgra_id, simplest_cgra = min(cgras_item, key=lambda item: item[1].getTileNum())

        tiles = simplest_cgra.tiles
        # Disables the boundary ports of a single cgra.
        configure_boundary_ports(
            cgra_id,
            tiles,
            self.cgra_rows,
            self.cgra_columns,
            self.id2shape_map,
            False,
        )

        return ParamCGRA(
            simplest_cgra.rows,
            simplest_cgra.columns,
            tiles,
            simplest_cgra.links,
            simplest_cgra.dataSPM,
            simplest_cgra.configMemSize,
        )
