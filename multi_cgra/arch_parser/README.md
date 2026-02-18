# Multi-CGRA ArchParser

Parses YAML architecture specs to construct the Multi-CGRA.

## Contents
- ArchParser.py – entry point that reads a YAML file and returns a MultiCgraParam.
- MultiCgraParam.py – describes the full grid of CGRAs.
- ParamCGRA.py – per-CGRA tiles, links, and memory.
- Tile.py – tile data structure.
- Link.py – directional links among tiles.
- DataSPM.py – scratchpad model shared by CGRAs.
- helper.py – utilities to build mesh links and enable boundary ports.
- test/ – tests about the ArchParser, extracts the MultiCgraParam from `architecture.yaml`, constructs a Multi-CGRA, and generates corresponding Verilog.

## Test
```python
pytest ArchParser_test.py --tb=short --arch_file </path/to/arch_file>
```
## Usage
Use `ArchParser` to extract the hardware configurations from `arch.yaml`:

`MeshMultiCgraTemplateRTL_test.py::test_mesh_multi_cgra_universal`:
```python
def test_mesh_multi_cgra_universal(cmdline_opts, arch_yaml_path = "arch.yaml"):
  arch_file = os.path.join(os.path.dirname(__file__), arch_yaml_path)
  print(f"Use the architecture file: {arch_file}")
  arch_parser = ArchParser(arch_file)
  multiCgraParam = arch_parser.parse_multi_cgra_param()
  
  print(f"multiCgraParam: {multiCgraParam}")
  singleCgraParam = multiCgraParam.cgras[0][0]
  num_cgra_rows = multiCgraParam.rows
  num_cgra_columns = multiCgraParam.cols
  per_cgra_rows = singleCgraParam.rows
  per_cgra_columns = singleCgraParam.columns
```
## ToDO
- [ ] Add parsing for more architectural parameters, such as memory capacity, link latency, link bandwidth.
