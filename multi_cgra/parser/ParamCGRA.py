class ParamCGRA:
    def __init__(self, rows, columns, tiles, links, dataSPM, configMemSize):
        self.rows = rows
        self.columns = columns
        self.tiles = tiles
        self.links = links
        self.dataSPM = dataSPM
        self.configMemSize = configMemSize

    def getValidTiles(self):
        return self.tiles

    def getValidLinks(self):
        return self.links

    def overrideTiles(self, tile_x, tile_y, operations, existence):
        row = tile_y
        col = tile_x
        self.tiles[row * self.columns + col].override(operations, existence)

    def overrideLinks(self, src_tile_x, src_tile_y, dst_tile_x, dst_tile_y, existence):
        # Finds the link and sets the disabled status.
        for link in self.links:
            # TODO(@benkangpeng): Handle the links between dataSPM and tile.
            if link.isFromMem() or link.isToMem():
                continue

            if (link.srcTile.dimX == src_tile_x and link.srcTile.dimY == src_tile_y and
                    link.dstTile.dimX == dst_tile_x and link.dstTile.dimY == dst_tile_y):
                link.disabled = not existence
                link.validatePorts()
                break

    def __repr__(self) -> str:
        return f"ParamCGRA(rows={self.rows}, columns={self.columns})"
