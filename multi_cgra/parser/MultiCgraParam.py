from ...lib.util.cgra.cgra_helper import get_links, keep_port_valid_on_boundary
from ...lib.util.cgra.Tile import Tile
from ...lib.util.cgra.DataSPM import DataSPM
from .ParamCGRA import ParamCGRA
import copy


class MultiCgraParam:
    def __init__(self, rows, cols, cgras):
        self.rows = rows
        self.cols = cols
        self.cgras = cgras

    @classmethod
    def from_params(
        cls, num_cgra_rows, num_cgra_cols, per_cgra_rows, per_cgra_cols
    ):
        """
        The constructor for customizing the MultiCgraParam.
        """
        # Restricted by ControllerRTL.
        assert (
            num_cgra_rows <= num_cgra_cols
        ), "multi_cgra_rows must be less than or equal to multi_cgra_columns."
        num_cgras = num_cgra_rows * num_cgra_cols
        # Restricted by data_mem_size_global(the power of 2).
        assert (num_cgras & (num_cgras - 1)) == 0, "num_cgras must be the power of 2."

        # Constructs tiles.
        tiles = []
        for r in range(per_cgra_rows):
            tiles.append([])
            for c in range(per_cgra_cols):
                tiles[r].append(Tile(c, r))

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
            keep_port_valid_on_boundary(
                cgra_id,
                tiles_flat,
                num_cgra_rows,
                num_cgra_cols,
                per_cgra_rows,
                per_cgra_cols,
            )

        dataSPM = DataSPM(per_cgra_cols, per_cgra_cols)
        id2dataSPM = {}
        id2ctrlMemSize_map = {}
        # TODO @benkangpeng Is ctrlMemSize in architecture.yaml?
        ctrlMemSize = 16

        for id in range(num_cgras):
            id2dataSPM[id] = dataSPM
            id2ctrlMemSize_map[id] = ctrlMemSize

        cgras = []
        for cgraRow in range(num_cgra_rows):
            cgras.append([])
            for cgraCol in range(num_cgra_cols):
                id = cgraRow * num_cgra_cols + cgraCol
                cgras[cgraRow].append(
                    ParamCGRA(
                        per_cgra_rows,
                        per_cgra_cols,
                        id2validTiles[id],
                        id2validLinks[id],
                        id2dataSPM[id],
                        id2ctrlMemSize_map[id],
                    )
                )

        return cls(num_cgra_rows, num_cgra_cols, cgras)

    def __repr__(self):
        return (
            f"\nSize of MultiCGRAs: {self.rows}x{self.cols}\n"
            + f"Size of CGRA(Tiles): {self.cgras[0][0].rows}x{self.cgras[0][0].columns}"
        )
