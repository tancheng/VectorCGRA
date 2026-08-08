# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, Codex, and
others) when working with code in this repository. Claude Code picks it
up via the `@AGENTS.md` import in `CLAUDE.md`; agents that follow the
AGENTS.md convention read it directly.

## Project overview

VectorCGRA is a parameterizable CGRA (Coarse-Grained Reconfigurable Accelerator)
generator written in PyMTL3. The Python "RTL" both simulates cycle-accurately and
translates to synthesizable Verilog via Verilator.

## Environment setup

The project requires a **custom PyMTL3 fork**, not upstream pymtl3:

```bash
python3 -m venv ${HOME}/venv && source ${HOME}/venv/bin/activate
pip install py==1.11.0 wheel hypothesis pytest py-markdown-table
pip install -U git+https://github.com/tancheng/pymtl3.1@yo-struct-list-fix
git submodule update --init   # fu/dp_fpfma, fu/pymtl3_hardfloat, noc/PyOCN
```

Verilog translation/import additionally needs `verilator` and `pkg-config` on
PATH (CI pins verilator 4.036; newer verilator may fail the *import/build* step
with obj_dir naming mismatches even though translation itself succeeded — treat
`FileNotFoundError: obj_dir_.../V..._classes.mk` as a local-toolchain issue,
not a code bug, and let CI arbitrate).

## Running tests

```bash
pytest mem/register_cluster/test/ -q          # one component's tests
pytest tile/test/TileRTL_test.py::test_tile_alu -q     # single test
pytest .. -v --tb=short                       # full suite (from a build/ dir; hours)
python3 local_CI.py                           # mirrors CI locally (run from build/)
```

- Test discovery follows `pytest.ini`: files `*_test.py`, functions `test*`.
  Default `addopts` hide tracebacks (`--tb=no`) — pass `--tb=short`/`--tb=long`
  to see failures.
- **The default pytest run does NOT exercise Verilog translation.** Pass
  `--test-verilog` (a pymtl3 pytest plugin option) to force RTLIR → Verilog →
  Verilator import. New RTL constructs must be validated this way; plain
  simulation passing proves nothing about translatability.
- Component tests run in seconds. CGRA-level tests simulate whole fabrics in
  pure Python: `CgraRTL_test` minutes, 4x4 FIR ~3 min, weight-stationary
  systolic ~17 min, migration suite ~25 min. A test failing with
  `assert N < N` (max_cycles) means the kernel **deadlocked/stalled**, not that
  data was wrong.
- CI (`.github/workflows/python-package.yml`) takes **~3.5–4.5 hours** per run
  and is the source of truth. It runs the full suite plus explicit
  `--test-verilog --dump-vtb --dump-vcd` invocations, sv2v, and yosys synthesis.

## PyMTL3 / RTLIR constraints (verified the hard way)

- RTLIR (the Verilog translator) rejects `in` / `not in` on hardware values and
  rejects tuple-valued free variables inside `@update` blocks. Spell out
  comparisons (`(x != A) & (x != B)`), or load constants into `Wire` arrays at
  construct time (`s.lut[i] //= Type(const)`) and index those.
- Assigning to a bit-slice with `<<=` inside `@update_ff` silently does nothing
  in simulation. Compute one-hot set/clear masks combinationally with `@=` and
  assign the whole vector once: `s.state <<= (s.state | set_mask) & ~clear_mask`.
- Python-level constants (ints, loop bounds) referenced in update blocks are
  constant-folded; full Python is available at construct/elaboration time.
- An unread interface input needs no driver, but the moment RTL starts reading
  it, every instantiation site must drive it or elaboration fails with
  `NoWriterError` — check all three tile variants (see below) when adding ports.

## Architecture

Hierarchy: `multi_cgra/` (mesh/ring of CGRAs + controllers + NoC) → `cgra/`
(grid of tiles + data mem + controller + ctrl ring) → `tile/` (FU cluster
`fu/flexible/FlexibleFuRTL`, routing crossbar, FU crossbar, register cluster,
ctrl memory, const queue). `lib/` holds message/ctrl-type factories
(`mk_ctrl`, `mk_intra_cgra_pkt`, ...), cmd opcodes (`lib/cmd_type.py`), and
shared constants (`lib/util/common.py`).

- **Everything is val/rdy** (`lib/basic/val_rdy/ifcs.py`). FUs combinationally
  derive `recv_in[i].rdy` from `send_out.rdy` (see `fu/single/AdderRTL.py`), so
  a backpressure path that feeds an FU's output readiness back into its input
  readiness creates a **combinational loop**. This has bitten repeatedly; keep
  write/backpressure gates a function of registered state only.
- **Ctrl-step protocol**: each tile executes a small program of ctrl words from
  `CtrlMemDynamicRTL`. A step can last many cycles; the tile latches per-consumer
  done bits (`element_done`, `*_crossbar_done`) and the step completes when
  `ctrl_mem.send_ctrl.val & rdy` fires — that pulse (`ctrl_proceed`) is what
  advances the const queue and consumes register-bank tokens. Within a step,
  operand signals are level-like: FUs may accept an operand several times
  (vector-factor replays) or **snoop `recv_in[*].val/msg` without ever asserting
  `rdy`** (`fu/vector/VectorAllReduceRTL`). Never assume one val/rdy handshake
  per operand per step.
- **Register cluster semantics** (`mem/register_cluster/`): never-written
  ("unarmed") registers always assert `val` on a configured read — existing
  kernels deliberately read registers nothing writes, as a default-token source
  for liveness. Once written, token discipline applies (issue #321). Token
  state is cleared on task switch via the tile `clear` signal (asserted on
  `CMD_TERMINATE` in `TileWithContextSwitchRTL`).
- **Three tile variants** must stay in sync when the tile-internal interface
  changes: `TileRTL`, `TileWithContextSwitchRTL` (task switching/migration),
  `TileWithStreamingLoadRTL` (no register→routing-crossbar path; ties it off).
- **Kernels are encoded in tests**: cgra/multi_cgra tests build per-tile lists
  of `CMD_CONFIG` packets (ctrl words) plus `CMD_CONST` / `CMD_LAUNCH` /
  `CMD_CONFIG_TOTAL_CTRL_COUNT` bookkeeping, then compare sink outputs.
  Changing component semantics usually means re-deriving expected sink
  sequences cycle-by-cycle; sinks (`lib/basic/val_rdy/SinkRTL.py`) check order,
  not cycle numbers, and stop accepting once their expected list is exhausted.
- The command-type dispatch in `ControllerRTL` forwards any inter-CGRA command
  without a dedicated handler to the ctrl ring (catch-all), so new `CMD_*`
  types work by default; `CtrlMemDynamicRTL`'s accept-list is curated and must
  be extended explicitly.

## Repo conventions

- Two-space indentation, `s.` for component attributes, one class per file
  named after it, tests under `<component>/test/`.
- Naming: classes and constructed type names are `CamelCase`
  (`RegisterBankRTL`, `DataType`); functions, methods, and variables are
  `snake_case` (`update_msg`, `token_valid`), including the `mk_*` type
  factories; constants are `UPPER_SNAKE_CASE` (`CMD_LAUNCH`,
  `READ_TOWARDS_FU`), with a small `kCamelCase` family for struct
  attribute keys (`kAttrPayload`).
- Generated artifacts (`*__pickled.v`, `*_v.cpp`, `obj_dir_*`) land in the
  working directory; they are untracked — clean them before committing.
- Branch protection on `master`: PR required, 1 approving review (authors
  cannot self-approve), and both `build (3.9.20)` / `build (3.12.8)` checks
  must pass.
