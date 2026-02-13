# Change: Enable MemUnit Fusion in Combo FUs

## Why
Currently, when performing pattern fusion into single FUs (e.g., MAC = mul+add), `MemUnitRTL` cannot be fused with other operations. The combo FUs (`TwoSeqCombo`, `TwoPrlCombo`, `ThreeCombo`, `FourCombo`) force memory ports to be dangling (tied to 0), and `TileRTL` only connects memory ports for standalone `MemUnitRTL` FUs, not combo FUs that may contain `MemUnitRTL`.

This prevents useful fusion patterns like `ADD_CONST + LD` (address computation fused with load) from being implemented as single-cycle operations.

## What Changes
- **Combo FUs**: Modify `TwoSeqCombo`, `TwoPrlCombo`, `ThreeCombo`, and `FourCombo` to propagate memory interfaces from internal FUs instead of tying them to 0
- **TileRTL**: Update memory port connection logic to detect combo FUs that contain `MemUnitRTL` and connect their memory ports appropriately
- **FlexibleFuRTL**: Already correctly exposes per-FU memory ports; no changes needed

## Impact
- Affected specs: `functional-units` (new capability spec)
- Affected code:
  - `fu/basic/TwoSeqCombo.py`
  - `fu/basic/TwoPrlCombo.py`
  - `fu/basic/ThreeCombo.py`
  - `fu/basic/FourCombo.py`
  - `tile/TileRTL.py`
- Tests: Need to add tests for combo FUs containing `MemUnitRTL`
