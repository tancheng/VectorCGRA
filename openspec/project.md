# Project Context

## Purpose
VectorCGRA (Vectorizable Coarse-Grained Reconfigurable Accelerator) is a parameterizable CGRA generator that produces synthesizable Verilog for different CGRA architectures based on user-specified configurations. Key capabilities include:
- Configurable CGRA size (width × height tiles)
- Customizable functional units per tile
- Vector lane support for SIMD operations
- Multiple topologies (Mesh, King Mesh)
- Multi-CGRA interconnection (Ring, Mesh topologies)
- Context switching support

## Tech Stack
- **Primary Language**: Python 3.9/3.12
- **Hardware Description**: PyMTL3 (Python-based RTL modeling framework)
- **Verilog Generation**: PyMTL3 translation passes with Verilator backend
- **Testing**: pytest with PyMTL3 test utilities
- **Simulation**: Verilator 4.036
- **Synthesis**: sv2v + Yosys (via mflowgen)
- **Dependencies**:
  - PyMTL3 (custom fork: `tancheng/pymtl3.1@yo-struct-list-fix`)
  - hypothesis (property-based testing)
  - PyYAML (configuration parsing)
  - graphviz (visualization)
  - py-markdown-table (documentation)

## Project Conventions

### Code Style
- **File naming**: `<ModuleName>RTL.py` for RTL components, `<ModuleName>FL.py` for functional-level models
- **Test files**: `<ModuleName>_test.py` in `test/` subdirectory
- **Class naming**: PascalCase with RTL/FL suffix (e.g., `TileRTL`, `CgraRTL`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `OPT_ADD`, `CMD_CONFIG`)
- **Signal naming**: snake_case (e.g., `recv_data`, `send_to_controller_pkt`)
- **File headers**: Include author attribution and date in docstring
- **Comments**: Use `#=========================================================================` for section separators

### Architecture Patterns
- **Hierarchical RTL composition**: Components use PyMTL3's `construct()` method with explicit port connections
- **Interface conventions**:
  - `RecvIfcRTL` / `SendIfcRTL`: Val/Rdy handshaking interfaces
  - Port naming: `recv_*` for inputs, `send_*` for outputs
  - `//=` operator for port connections
- **Type factory functions**: Use `mk_*` functions to create parameterized bitstruct types (e.g., `mk_data()`, `mk_ctrl()`, `mk_intra_cgra_pkt()`)
- **Attribute constants**: Define field names as string constants in `lib/util/data_struct_attr.py` (e.g., `kAttrPayload`, `kAttrData`)
- **Flexible functional units**: Use `FlexibleFuRTL` wrapper with configurable `FuList` parameter
- **Tile-based architecture**: Each tile contains FUs, crossbars, register cluster, ctrl memory, and const memory
- **Control flow**: Ring network for control packet distribution, mesh/king-mesh for data routing

### Testing Strategy
- **Test framework**: pytest with PyMTL3's `run_sim()` helper
- **Test harness pattern**: Create `TestHarness` class wrapping DUT with `TestSrcRTL`/`TestSinkRTL`
- **Simulation levels**:
  - Pure Python simulation (default)
  - Verilog translation + Verilator simulation (`--test-verilog`)
- **Test artifacts**:
  - `--dump-vtb`: Generate Verilog test bench
  - `--dump-vcd`: Generate waveform dump
- **Verilator warnings**: Configure via `VerilogVerilatorImportPass.vl_Wno_list` metadata
- **File pattern**: `python_files = *_test.py`, `python_functions = test test_*`

### Git Workflow
- **Default branch**: `master`
- **Feature branches**: Named after issue number (e.g., `214-p3-memunit-is-not-fusible`)
- **CI/CD**: GitHub Actions on push/PR to master
  - Matrix testing: Python 3.9.20, 3.12.8
  - Simulation + Verilog translation tests
  - Synthesis validation (Yosys, max 15 min)

## Domain Context
- **CGRA**: Coarse-Grained Reconfigurable Array - spatial computing architecture with configurable tiles
- **Tile**: Processing element containing functional units, routing crossbars, and local storage
- **Functional Unit (FU)**: Computation primitive (Adder, Multiplier, MemUnit, etc.)
- **Crossbar**: Routing network connecting tile ports to FU inputs/outputs
- **Control Memory**: Stores per-cycle configuration for FU operation selection and routing
- **Const Memory**: Queue for immediate/constant values
- **Register Cluster**: Local register file banks per tile
- **Val/Rdy Protocol**: Handshake where producer asserts `val`, consumer asserts `rdy`, transfer occurs when both high
- **Operations**: Defined in `lib/opt_type.py` (e.g., `OPT_ADD`, `OPT_MUL`, `OPT_LD`, `OPT_VEC_ADD`)
- **Commands**: Defined in `lib/cmd_type.py` (e.g., `CMD_CONFIG`, `CMD_LAUNCH`, `CMD_COMPLETE`)

## Important Constraints
- **Verilator version**: 4.036 (specific version required for compatibility)
- **PyMTL3 fork**: Must use custom fork with struct list fix
- **Synthesis time**: CGRA template synthesis must complete within 15 minutes
- **Python compatibility**: Must work on Python 3.7/3.8/3.9/3.10/3.12
- **Submodules**: PyOCN network library is a git submodule (requires `git submodule update --init`)
- **Build directory**: Tests should run from `build/` directory

## External Dependencies
- **PyOCN**: Network-on-Chip library (`noc/PyOCN/`) - ring and mesh network implementations
- **pymtl3_hardfloat**: Floating-point unit support (submodule in `fu/pymtl3_hardfloat/`)
- **mflowgen**: Physical design flow automation for synthesis
- **sv2v**: SystemVerilog to Verilog converter for synthesis compatibility
