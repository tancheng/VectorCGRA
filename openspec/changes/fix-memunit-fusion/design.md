## Context
The CGRA tile architecture allows flexible functional units through `FlexibleFuRTL`, which wraps a list of FUs. Each FU exposes memory interfaces (`to_mem_raddr`, `from_mem_rdata`, `to_mem_waddr`, `to_mem_wdata`) that are aggregated in `FlexibleFuRTL` as arrays indexed by FU position.

Currently, `TileRTL` connects these memory ports to the tile's external memory interface only when the FU at position `i` is exactly `MemUnitRTL`. However, combo FUs (like `TwoSeqCombo`, `ThreeCombo`, etc.) internally instantiate multiple FUs but expose only a single set of memory ports that are tied to 0.

## Goals / Non-Goals
### Goals
- Enable `MemUnitRTL` to be used as a component within combo FUs
- Propagate memory interface signals from internal `MemUnitRTL` through combo FU wrappers
- Maintain backward compatibility with existing non-memory combo FUs

### Non-Goals
- Supporting multiple `MemUnitRTL` instances within a single combo FU (only one memory access per cycle is supported at tile level)
- Adding new memory access patterns or operations
- Changing the memory interface protocol

## Decisions

### Decision 1: Propagate memory signals from internal FUs in combo classes
**What**: In combo FU base classes, connect the internal FU's memory ports to the combo's external memory ports using OR logic (similar to `LinkOrRTL`).

**Why**: This allows memory signals to pass through when any internal FU is a `MemUnitRTL`. The OR approach works because:
1. Only one internal FU will be actively using memory at a time (enforced by operation type)
2. Non-memory FUs tie their memory ports to 0, so OR-ing with them is a no-op

**Alternatives considered**:
- MUX-based selection: More complex, requires additional control signals
- Explicit MemUnit detection at combo construction: Would require factory functions and break simple inheritance pattern

### Decision 2: Detect combo FUs containing MemUnit in TileRTL
**What**: In `TileRTL`, check if a FU class has `MemUnitRTL` in its composition (via class attributes or inspection) rather than checking exact class equality.

**Why**: The current `FuList[i] == MemUnitRTL` check only matches standalone MemUnits. We need to also match combo FUs that contain MemUnit.

**Implementation approach**: 
- Add a class attribute `contains_mem_unit = True` to combo FUs that include `MemUnitRTL`
- Or use `hasattr(FuList[i], 'Fu0')` style introspection to detect combo FUs, then check their internal FU types
- Simplest: check if FU has a method/attribute indicating memory capability, defaulting to checking `== MemUnitRTL` for backward compatibility

## Risks / Trade-offs

### Risk: Multiple memory operations in same combo
**Mitigation**: Document that only one internal FU in a combo can be `MemUnitRTL`. The hardware will still work (OR of two memory requests), but behavior would be undefined.

### Risk: Timing impact
**Mitigation**: The OR logic for memory signals is purely combinational and adds minimal delay. Memory access timing is already the critical path.

## Open Questions
1. Should we add explicit validation to prevent multiple `MemUnitRTL` in a single combo FU?
2. Should we create a new combo FU class specifically for memory-compute fusion (e.g., `MemComputeCombo`) or modify existing classes?
