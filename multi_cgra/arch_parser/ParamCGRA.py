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
            #  handles the link from dataSPM to the 1st column of tiles.
            # `src_tile_x = src_tile_y = -1` indicates the source of the link is dataSPM.
            if link.isFromMem():
                if src_tile_x == -1 and src_tile_y == -1 and link.memPort == dst_tile_y:
                    link.disabled = not existence
                    link.validatePorts()
                    break
                else:
                    continue

            #  handles the link from the 1st column of tiles to dataSPM.
            # `dst_tile_x = dst_tile_y = -1` indicates the destination of the link is dataSPM.
            if link.isToMem():
                if dst_tile_x == -1 and dst_tile_y == -1 and link.memPort == src_tile_y:
                    link.disabled = not existence
                    link.validatePorts()
                    break
                else:
                    continue

            # handles the link between tiles.
            if (link.srcTile.dimX == src_tile_x and link.srcTile.dimY == src_tile_y and
                    link.dstTile.dimX == dst_tile_x and link.dstTile.dimY == dst_tile_y):
                link.disabled = not existence
                link.validatePorts()
                break

    def getFuNum(self):
        """Returns the total number of valid functional units in the CGRA."""
        return sum(tile.getFuNum() for tile in self.tiles if not tile.disabled)

    def __repr__(self) -> str:
        return f"ParamCGRA(rows={self.rows}, columns={self.columns})"
