class MultiCgraParam:
    def __init__(self, rows, cols, cgras):
        self.rows = rows
        self.cols = cols
        self.cgras = cgras

    def __repr__(self):
        return f'{self.rows}x{self.cols} cgras'