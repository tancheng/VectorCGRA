# VectorCGRA Agent Notes

This repository is the architectural reference for the integrated Chipyard CGRA.

## What matters most for the current SoC work

The active Chipyard integration does not use every architecture in this repository. The currently integrated blackbox corresponds to the generated `2x2 Mesh` variant, not the FIR-oriented `4x4 Mesh` or `2x2 KingMesh` examples.

Relevant files:

- Integrated reference generator:
  [cgra/translate/CgraRTL_2x2_translate.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/cgra/translate/CgraRTL_2x2_translate.py:1)

- General packet and control structure definitions:
  [lib/messages.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/lib/messages.py:1)
  [lib/cmd_type.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/lib/cmd_type.py:1)
  [lib/opt_type.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/lib/opt_type.py:1)
  [lib/util/common.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/lib/util/common.py:1)

## Architectures to distinguish

### Current Chipyard-integrated architecture

- `2x2`
- `Mesh`
- `tile_ports = 4`
- `FuList = [Adder, Mul, Logic, Shifter, Phi, Comp, Grant, MemUnit, Sel, Ret]`

See:
[cgra/translate/CgraRTL_2x2_translate.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/cgra/translate/CgraRTL_2x2_translate.py:42)

### FIR reference architecture that matches the command semantics better

- `4x4`
- `Mesh`
- same `tile_ports = 4`
- same 10-FU base list

See:
[cgra/test/CgraRTL_fir_test.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/cgra/test/CgraRTL_fir_test.py:143)

### FIR reference architecture that does not match the current integration

- `2x2`
- `KingMesh`
- `tile_ports = 8`
- extra FU variants

See:
[cgra/test/CgraRTL_fir_2x2_test.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/cgra/test/CgraRTL_fir_2x2_test.py:151)

## Best current smoke-test reference

For the current Chipyard integration, the best reference is:

- [cgra/test/CgraRTL_test.py::test_homogeneous_2x2](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/cgra/test/CgraRTL_test.py:596)

The packet sequence used by Chipyard was hand-ported from:

- [cgra/test/CgraRTL_test.py](/mnt/public/sichuan_a/qjj/CGRA-SoC/VectorCGRA/cgra/test/CgraRTL_test.py:260)

That sequence uses only:

- `CMD_CONFIG_TOTAL_CTRL_COUNT`
- `CMD_CONFIG_COUNT_PER_ITER`
- `CMD_CONFIG`
- `CMD_LAUNCH`

It is a full execution-flow smoke test, but not a full application kernel like FIR.

## FIR implications

For FIR return kernels, the reference tests use more than the minimal command set. Typical required commands include:

- `CMD_STORE_REQUEST`
- `CMD_CONST`
- `CMD_CONFIG_COUNT_PER_ITER`
- `CMD_CONFIG_TOTAL_CTRL_COUNT`
- `CMD_CONFIG`
- `CMD_CONFIG_PROLOGUE_*`
- per-tile `CMD_LAUNCH`

Therefore:

- a minimal `CONFIG + LAUNCH + WAIT` interface is not enough for FIR
- the Chipyard side must support either raw packet injection or a richer host API

## Packet format reminders

For the current integrated `2x2 Mesh` reference:

- `DataType = 35 bits`
- `CtrlType = 107 bits`
- `CgraPayload = 157 bits`
- `IntraCgraPkt = 182 bits`
- `InterCgraPkt = 185 bits`

These widths are architecture-dependent. Always re-check them if the architecture changes.

## Agent guidance

- If you need literal packet sequences, extract them from the exact reference test that matches the integrated architecture.
- Do not assume a FIR packet sequence from `KingMesh` can be replayed on the current `Mesh` integration.
- For host-side integration work, the current best path is:
  1. validate command coverage with `homogeneous_2x2`
  2. then switch hardware architecture if a richer kernel such as FIR is required
