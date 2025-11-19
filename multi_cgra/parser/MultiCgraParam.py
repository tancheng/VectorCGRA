class MultiCgraParam:
    def __init__(self, rows, cols, cgras):
        self.rows = rows
        self.cols = cols
        self.cgras = cgras

    def __repr__(self):
        return (
            f"Size of MultiCGRAs: {self.rows}x{self.cols}\n"
            + f"Size of CGRA(Tiles): {self.cgras[0][0].rows}x{self.cgras[0][0].columns}"
        )
