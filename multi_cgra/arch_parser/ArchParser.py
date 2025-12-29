import yaml
from .MultiCgraParam import MultiCgraParam
from ...lib.util.cgra.DataSPM import DataSPM
from ...lib.util.cgra.Tile import Tile
from .ParamCGRA import ParamCGRA
from ...lib.util.cgra.cgra_helper import *
import copy


class ArchParser:
    def __init__(self, yaml_file: str):
        with open(yaml_file, 'r') as f:
            self.yaml_data = yaml.safe_load(f)

        self.cgra_rows = self.yaml_data['multi_cgra_defaults']['rows']
        self.cgra_columns = self.yaml_data['multi_cgra_defaults']['columns']
        self.per_cgra_rows = self.yaml_data['cgra_defaults']['rows']
        self.per_cgra_columns = self.yaml_data['cgra_defaults']['columns']
        self.num_registers = self.yaml_data['tile_defaults']['num_registers']
        self.fu_types = self.yaml_data['tile_defaults']['fu_types']

    def parse_dataSPM(self):
        return DataSPM(self.per_cgra_rows, self.per_cgra_rows)

    def parse_tiles(self):
        """
        Parse the tiles in one CGRA.
        """
        tiles = []
        for r in range(self.per_cgra_rows):
            tiles.append([])
            for c in range(self.per_cgra_columns):
                """
                Mapping way of tiles in a single CGRA (Cartesian coordinate system):
                  ^
                  |   y (row) increases upward: 0 at the bottom, up to `per_cgra_rows-1` at the top
                  |
                  |   (row, col): (y, x)
                  +------------------------>
                  0                        x (column) increases to the right: 0 at the left, up to `per_cgra_columns-1` at the right
                """
                tiles[r].append(Tile(c, r, self.num_registers, self.fu_types))
        return tiles

    def parse_cgras(self):
        # Restricted by ControllerRTL.
        assert self.cgra_rows <= self.cgra_columns, "multi_cgra_rows must be less than or equal to multi_cgra_columns."
        num_cgras = self.cgra_rows * self.cgra_columns
        # Restricted by data_mem_size_global(the power of 2).
        assert (num_cgras & (num_cgras - 1)
                ) == 0, "num_cgras must be the power of 2."
        tiles = self.parse_tiles()

        # Gets the links.
        links = get_links(tiles)
        # flatten tiles.
        tiles_0 = [t for row in tiles for t in row]

        # cgra id to valid links.
        id2validLinks = {}
        # cgra id to valid tiles.
        id2validTiles = {}

        for id in range(num_cgras):
            id2validLinks[id] = copy.deepcopy(links)
            id2validTiles[id] = copy.deepcopy(tiles_0)

        # Iterates id2validTiles to enable boundary ports
        for cgra_id, tiles_flat in id2validTiles.items():
            configure_boundary_ports(
                cgra_id, tiles_flat, self.cgra_rows, self.cgra_columns, self.per_cgra_rows, self.per_cgra_columns)

        dataSPM = self.parse_dataSPM()
        id2dataSPM = {}
        id2ctrlMemSize_map = {}
        ctrlMemSize = self.yaml_data['cgra_defaults']['configMemSize']

        for id in range(num_cgras):
            id2dataSPM[id] = dataSPM
            id2ctrlMemSize_map[id] = ctrlMemSize

        cgras = []
        for cgra_row in range(self.cgra_rows):
            cgras.append([])
            for cgra_col in range(self.cgra_columns):
                id = cgra_row * self.cgra_columns + cgra_col
                cgras[cgra_row].append(ParamCGRA(
                    self.per_cgra_rows, self.per_cgra_columns, id2validTiles[id], id2validLinks[id], id2dataSPM[id], id2ctrlMemSize_map[id]))

        # Overrides the tiles.
        if 'tile_overrides' in self.yaml_data:
            data = self.yaml_data['tile_overrides']
            for override in data:
                fu_types = [] if not override['existence'] else override['fu_types']
                cgras[override['cgra_x']][override['cgra_y']].overrideTiles(override['tile_x'], override['tile_y'], fu_types, override['existence'])

        # Overrides the links.
        if 'link_overrides' in self.yaml_data:
            data = self.yaml_data['link_overrides']
            for override in data:
                 if override['src_cgra_x'] == override['dst_cgra_x'] and override['src_cgra_y'] == override['dst_cgra_y']:
                     cgras[override['src_cgra_x']][override['src_cgra_y']].overrideLinks(
                         override['src_tile_x'], override['src_tile_y'],
                         override['dst_tile_x'], override['dst_tile_y'],
                         override['existence']
                     )
        return cgras

    def parse_multi_cgra_param(self):
        cgras = self.parse_cgras()
        return MultiCgraParam(self.cgra_rows, self.cgra_columns, cgras)

    def get_simplest_cgra_param(self) -> ParamCGRA:
        """Returns the simplest(has the least number of functional units) CGRA parameter."""
        cgras = self.parse_cgras()
        # set of (cgra_id, cgra)
        cgras_item = (
            ( i * self.cgra_columns + j , cgras[i][j] )
            for i in range(self.cgra_rows)
            for j in range(self.cgra_columns)
        )
        # Finds the cgra which has the least number of FUs.
        cgra_id, simplest_cgra = min(cgras_item, key=lambda item: item[1].getFuNum())

        tiles = simplest_cgra.tiles
        # Disables the boundary ports of a single cgra.
        configure_boundary_ports(cgra_id, tiles, self.cgra_rows, self.cgra_columns,
                                self.per_cgra_rows, self.per_cgra_columns, False)

        return ParamCGRA(simplest_cgra.rows, simplest_cgra.columns, tiles, simplest_cgra.links, 
                         simplest_cgra.dataSPM, simplest_cgra.configMemSize)
