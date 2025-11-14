import yaml
from .MultiCgraParam import MultiCgraParam
from .DataSPM import DataSPM
from .Tile import Tile
from .ParamCGRA import ParamCGRA
from .helper import *
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
        per_cgra_rows = self.yaml_data['cgra_defaults']['rows']
        per_cgra_columns = self.yaml_data['cgra_defaults']['columns']
        tiles = self.parse_tiles()

        # get the links of 2x2 tiles
        links = get_links_2x2(tiles)
        # 2x2 cgras
        id2validLinks = {
            0: links,
            1: links,
            2: links,
            3: links,
        }
        # flatten tiles.
        tiles_0 = [t for row in tiles for t in row]
        tiles_1 = copy.deepcopy(tiles_0)
        tiles_2 = copy.deepcopy(tiles_0)
        tiles_3 = copy.deepcopy(tiles_0)

        # cgra id to valid tiles.
        id2validTiles = {
            0: tiles_0,
            1: tiles_1,
            2: tiles_2,
            3: tiles_3,
        }
        # Iterates id2validTiles to enable boundary ports
        for cgra_id, tiles_flat in id2validTiles.items():
            keep_port_valid_on_boundary(
                cgra_id, tiles_flat, num_cgra_rows, num_cgra_columns, per_cgra_rows, per_cgra_columns)


        dataSPM = self.parse_dataSPM()
        id2dataSPM = {
            0: dataSPM,
            1: dataSPM,
            2: dataSPM,
            3: dataSPM
        }
        # Is ctrlMemSize in architecture.yaml?
        id2ctrlMemSize_map = {
            0: 16,
            1: 16,
            2: 16,
            3: 16
        }
        per_cgra_rows = self.yaml_data['cgra_defaults']['rows']
        per_cgra_columns = self.yaml_data['cgra_defaults']['columns']
        
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
