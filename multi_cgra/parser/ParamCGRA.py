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
    
    def __repr__(self) -> str:
        return f"ParamCGRA(rows={self.rows}, columns={self.columns})"
    