# Multi-CGRA Parser

Parses YAML architecture specs to construct the Multi-CGRA.

## Contents
- Parser.py – entry point that reads a YAML file and returns a MultiCgraParam.
- MultiCgraParam.py – describes the full grid of CGRAs.
- ParamCGRA.py – per-CGRA tiles, links, and memory.
- Tile.py – tile data structure.
- Link.py – directional links among tiles.
- DataSPM.py – scratchpad model shared by CGRAs.
- helper.py – utilities to build mesh links and enable boundary ports.
- test/ – test about the parser, extracting the MultiCgraParam from architecture.yaml and construct a Multi-CGRA.

## Usage
```python
from multi_cgra.parser import Parser

parser = Parser("path/to/architecture.yaml")
multi_cgra_param = parser.parse_multi_cgra_param()
```
## ToDO
- [ ] Add parsing for more architectural parameters, such as memory capacity, link latency, link bandwidth.
