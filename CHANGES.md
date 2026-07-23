# CHANGES

## Fix: OPT_STR ignores predicate, causing spurious store during drain cycles

### Symptom

GEMV kernel (`gemv.yaml`) produces incorrect results: `y[0]` at address 20
reads back as 0 instead of the expected 30. Addresses 21-23 are correct.
The execution trace confirms the correct value (30) is computed and stored
at cycle 233, but a spurious store at cycle 376 overwrites it with 0.

### Root Cause

In `fu/single/MemUnitRTL.py`, the `OPT_STR` (store) branch sets
`to_mem_waddr.val` and `to_mem_wdata.val` based solely on input `val`
signals, without checking the `predicate` bit:

```python
# BEFORE (buggy)
s.to_mem_waddr.val @= s.recv_all_val
s.to_mem_wdata.val @= s.recv_all_val
```

During pipeline drain cycles after the outer loop's `GRANT_ONCE` expires,
data flows through the pipeline with `predicate=0` but `val=1`. The store
FU treats this as a valid write and commits it to memory, overwriting
the correct result at address 20 with the new (invalid) accumulator value 0.

By contrast, `OPT_STR_CONST`, `OPT_LD`, and `OPT_ADD_CONST_LD` already
guard their memory accesses with predicate checks, so only `OPT_STR` is
affected.

### Trace Evidence (cycle 376, tile 2)

```
fu input[0]: payload=20  predicate=0  val=1   <-- addr, predicate=0
fu input[1]: payload=0   predicate=0  val=1   <-- data, predicate=0
mem_access wdata: payload=0  predicate=0  val=1  <-- store fires anyway
```

### Fix

`fu/single/MemUnitRTL.py` lines 201-207: gate `to_mem_waddr.val` and
`to_mem_wdata.val` on both inputs' predicates, consistent with
`OPT_STR_CONST`:

```python
# AFTER (fixed)
s.to_mem_waddr.val @= s.recv_all_val & \
                      s.recv_in[s.in0_idx].msg.predicate & \
                      s.recv_in[s.in1_idx].msg.predicate
s.to_mem_wdata.val @= s.recv_all_val & \
                      s.recv_in[s.in0_idx].msg.predicate & \
                      s.recv_in[s.in1_idx].msg.predicate
```
