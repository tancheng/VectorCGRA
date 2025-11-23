import yaml
from .MultiCgraParam import MultiCgraParam
from ...lib.cgra.DataSPM import DataSPM
from ...lib.cgra.Tile import Tile
from .ParamCGRA import ParamCGRA
from ...lib.cgra.cgra_helper import *
import copy


class Parser:
    def __init__(self, yaml_file: str):
        with open(yaml_file, 'r') as f:
            self.yaml_data = yaml.safe_load(f)

    def parse_dataSPM(self):
        per_cgra_columns = self.yaml_data['cgra_defaults']['columns']
        return DataSPM(per_cgra_columns, per_cgra_columns)

    def parse_tiles(self):
        """
        Parse the tiles in one CGRA.
        """
        tiles = []
        per_cgra_rows = self.yaml_data['cgra_defaults']['rows']
        per_cgra_columns = self.yaml_data['cgra_defaults']['columns']
        for r in range(per_cgra_rows):
            tiles.append([])
            for c in range(per_cgra_columns):
                tiles[r].append(Tile(c, r))
        return tiles

    def parse_cgras(self):
        num_cgra_rows = self.yaml_data['multi_cgra_defaults']['rows']
        num_cgra_columns = self.yaml_data['multi_cgra_defaults']['columns']
        # Restricted by ControllerRTL.
        assert num_cgra_rows <= num_cgra_columns, "multi_cgra_rows must be less than or equal to multi_cgra_columns."
        num_cgras = num_cgra_rows * num_cgra_columns
        # Restricted by data_mem_size_global(the power of 2).
        assert (num_cgras & (num_cgras - 1)
                ) == 0, "num_cgras must be the power of 2."
        per_cgra_rows = self.yaml_data['cgra_defaults']['rows']
        per_cgra_columns = self.yaml_data['cgra_defaults']['columns']
        tiles = self.parse_tiles()

        # Gets the links.
        links = get_links(tiles)
        # flatten tiles.
        tiles_0 = [t for row in tiles for t in row]

        # cgra id to valid links.
        id2validLinks = {}
        # cgra id to valid tiles.
        id2validTiles = {}

        for id in range(num_cgra_rows * num_cgra_columns):
            id2validLinks[id] = copy.deepcopy(links)
            id2validTiles[id] = copy.deepcopy(tiles_0)

        # Iterates id2validTiles to enable boundary ports
        for cgra_id, tiles_flat in id2validTiles.items():
            keep_port_valid_on_boundary(
                cgra_id, tiles_flat, num_cgra_rows, num_cgra_columns, per_cgra_rows, per_cgra_columns)

        dataSPM = self.parse_dataSPM()
        id2dataSPM = {}
        id2ctrlMemSize_map = {}
        # Is ctrlMemSize in architecture.yaml?
        ctrlMemSize = 16

        for id in range(num_cgra_rows * num_cgra_columns):
            id2dataSPM[id] = dataSPM
            id2ctrlMemSize_map[id] = ctrlMemSize

        cgras = []
        for cgraRow in range(num_cgra_rows):
            cgras.append([])
            for cgraCol in range(num_cgra_columns):
                id = cgraRow * num_cgra_columns + cgraCol
                cgras[cgraRow].append(ParamCGRA(
                    per_cgra_rows, per_cgra_columns, id2validTiles[id], id2validLinks[id], id2dataSPM[id], id2ctrlMemSize_map[id]))

        return cgras

    def parse_multi_cgra_param(self):
        cgras = self.parse_cgras()
        num_cgra_rows = self.yaml_data['multi_cgra_defaults']['rows']
        num_cgra_cols = self.yaml_data['multi_cgra_defaults']['columns']
        return MultiCgraParam(num_cgra_rows, num_cgra_cols, cgras)
