# Reading STEP CGRA Mapping Files

A file in `cgra/test/dfg_mappings` is a control-flow graph of configurations. Each `cfg_N` is one CGRA snapshot: active threads, RF inputs, active tiles, memory ports, writebacks, and the next configuration(s).

## Top Level

- `cgra_def`: hardware shape. In these examples: 4x4 tiles, 8 directional ports per tile (`N,S,W,E,NW,NE,SE,SW`), 3 FU inputs, 1 FU output, 16 read ports, 8 write ports, 2 load ports, 2 store ports, 16 data regs, and 16 predicate regs.
- `meta`: whole-program summary (`basic_block_count`, `node_count`, `thread_id_bounds`, format).
- `cfg_0 ... cfg_n`: executable configurations.

## What One `cfg` Does

1. `cfg_id` selects the configuration; `start_cfg=1` marks an entry point.
2. Threads in `[thread_count_min, thread_count_max)` execute it. `thread_count` is the intended span.
3. Enabled RF read ports (`in_regs_val`) inject operands. `"tid"` or `in_tid_enable=1` injects the current thread id instead of a register value.
4. Non-`OPT_NAH` tiles compute and route values across the fabric.
5. West/east boundary outputs write back to RF or predicate RF. North outputs drive load addresses. South outputs drive store data/address.
6. The tokenizer decides when a read port may fire again by waiting for the sinks named in its route row to return tokens.
7. If `branch_en=1`, the controller waits for predicate register `pred_reg_id` to be written for all active threads, then selects `branch_true_cfg_id` or `branch_false_cfg_id`; `reconverge_cfg_id` marks where paths rejoin.

## Metadata Fields

- `cmd`: `3` in these files means `CMD_CONFIG`.
- `cfg_id`: current configuration id.
- `br_id`: static fall-through / prefetched next config id. In linear regions it is usually the next `cfg`.
- `tile_load_count`: number of active tile bitstreams that must be loaded. It should match the number of tiles whose `opt_type != OPT_NAH`.
- `pred_tile_valid`: per-tile predicate enable coming from RF. These samples keep it all `1`.
- `ld_enable[k]`, `ld_reg_addr[k]`: enable load port `k`; returning data writes RF register `ld_reg_addr[k]`.
- `st_enable[k]`: enable store port `k`.
- `ld_base_addr`: present in JSON, but not consumed by the current loader; address generation is usually done explicitly in tiles.
- `in_regs[i]`, `in_regs_val[i]`: RF register sourced on read port `i`.
- `in_pred_regs[i]`, `in_pred_en[i]`, `in_pred_inv[i]`: read port `i` is guarded by predicate register `pX`, optionally inverted.
- `in_const_vals[i]`, `in_pred_reset_const_en[i]`: fallback constant for a predicated read when the predicate is false or was reset at reconvergence.
- `out_regs[i]`, `out_regs_val[i]`: data writeback destination on write port `i`.
- `out_pred_regs[i]`, `out_pred_regs_val[i]`: predicate writeback destination on write port `i`. The written value is the predicate bit arriving at the same west/east boundary return port.
- `end_cfg`: terminal marker. Final configs often also perform stores.
- `branch_backedge_sel`: `0` none, `1` true path is the loop backedge, `2` false path is the loop backedge.

## Tile Bitstream Fields

- `id`: local tile id. For these 4x4 mappings, `id = row*4 + col`. The key name like `tile_7_[1,1]` is just a label; the bracketed coordinates are 1-based `[x,y]`.
- `opt_type`: tile operation. `OPT_NAH` means inactive. `OPT_EXT` is treated as `OPT_PAS` by the loader.
- `tile_in_route`: up to 3 input directions feeding FU operands.
- `tile_out_route`: directions that receive the FU result.
- `tile_fwd_route[in][out]`: bypass path from tile input `in` directly to output `out`, without using the FU. The matrix uses absolute port order `N,S,W,E,NW,NE,SE,SW` on both axes. Many `OPT_PAS` tiles in these mappings are really pure forwarders described by this matrix.
- `tile_pred_route`: directions that carry the tile's predicate output.
- `pred_gen`: predicate comes from the FU result bit, typically for compare tiles such as `OPT_EQ_CONST` or `OPT_LT_CONST`.
- `pred_based_sel_in_to_out_route`: if the tile's incoming predicate is false, forward this input direction to the normal outputs instead of the FU result. This is the predicated-bypass mechanism.
- `const_val`: immediate for `*_CONST` ops and some passthrough patterns. Use hex if exact bit patterns matter.
- `tile_out_shift_amounts`: per-output delay through the tile's shift-register bank. The same delay applies to data and predicate on that output.
- `pred_fwd_route`: appears in some JSONs but is ignored by `generateCPUPktFromJSON`; current predicate behavior comes from `tile_pred_route`, `tile_fwd_route`, and `pred_based_sel_in_to_out_route`.

## Port Mapping Needed For A Per-Config DFG

- Read ports are grouped by row: `4*r + {0,1,2,3}` = west, southwest, east, southeast inputs for row `r`.
- Write ports are grouped by row: `2*r + {0,1}` = west, east outputs for row `r`.
- Load ports are hard-wired to north boundary columns `0` and `3`.
- Store ports are hard-wired to south boundary column pairs `(0=data, 1=addr)` and `(2=data, 3=addr)`.

## Tokenizer Meaning

- `token_route_sink_enable[rd][sink] = 1` means read port `rd` cannot re-issue until sink `sink` returns a token.
- Sink order is `wr0..wr7`, then `ld0..ld1`, then `st0..st1`.
- `token_route_delay_to_sink[sink]` is the return latency for that sink.
- If an enabled write/load/store sink is missing from all tokenizer rows, the current loader auto-attaches it to the last active read port.
- This is a dependence graph, not a data-routing graph.
- If you need to match `STEP_CgraRTL_mapped.py` exactly, its validation path normalizes write sinks `0..3` into physical tokenizer order `0,2,1,3`.

## How To Build A Per-Config Dataflow Graph

1. Create one subgraph per `cfg_N`.
2. Add source nodes for each enabled read port, plus `TID`, constants, and load responses.
3. Add one node per active tile (`opt_type != OPT_NAH`).
4. Connect nodes using `tile_in_route`, `tile_out_route`, `tile_fwd_route`, `tile_pred_route`, and the boundary port mapping above.
5. Add sink nodes for RF writes, predicate writes, loads, and stores from `out_*`, `ld_*`, and `st_*`.
6. Add control successor edges from the config to `br_id` or to `branch_true_cfg_id` / `branch_false_cfg_id`.
7. Use the tokenizer as dependency and latency annotations on the subgraph, not as ordinary data edges.

Across the sample mappings, `cfg_0` usually seeds base addresses or loop-carried state, middle configs either compute or generate a branch predicate, and the last config often drains results to the south store ports.
