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
    
    def __repr__(self) -> str:
        return f"ParamCGRA(rows={self.rows}, columns={self.columns})"
    