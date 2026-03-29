# CV6 Integration

This directory contains a barebones STEP host-integration environment built beside the
local Ara/CVA6 checkout at [`ara`](./ara).

What is included:

- A copied STEP generated RTL at [`rtl/step/STEP_CgraRTL__2c9482af1bbb680a__pickled.v`](./rtl/step/STEP_CgraRTL__2c9482af1bbb680a__pickled.v)
- A lightweight MMIO/DMA-style wrapper around the STEP ports
- A replay master that converts existing STEP generated examples into MMIO packet writes
- A standalone replay testbench and Makefile
- A real CVA6/Ariane core boundary module at [`rtl/cv6/cv6_step_core_boundary.sv`](./rtl/cv6/cv6_step_core_boundary.sv) for the next hookup step against the local Ara/CVA6 sources
- A bare-metal CV6 MMIO/DMA payload under [`sw`](./sw) and generators that turn the existing STEP testbench cases into CPU-consumable packet arrays

What is intentionally not included in this first drop:

- Edits to the local Ara tree
- A full Cheshire/Linux platform
- A production DMA engine
- A complete CVA6 software runtime

Current bring-up flow:

1. Generate a replay script from an existing STEP generated Verilog testbench:
   `make gen_gemm`
2. Build and run the local replay simulation:
   `make sim_replay`

Current CPU-driven flow:

0. Create or activate the dedicated tool env:
   `conda activate step_cv6_test`
1. Generate the packet header from the existing STEP testbench:
   `make gen_cpu_gemm`
2. Build the bare-metal CV6 image and convert it to a DRAM init file:
   `make build_cpu_gemm`
3. Build and run the CV6 harness:
   `make sim_cv6_gemm`

The helper script consumes the generated STEP testbench and `.cases` file, extracts:

- metadata packet transactions
- bitstream packet transactions
- terminal completion expectation

and emits a compact hex script for the replay master.

Notes:

- The CPU-driven path now builds against the upstream CVA6 `core/Flist.cva6`
  manifest using the `cv32a6_imac_sv32` config instead of the old mixed
  `z_rtl_files` closure.
- The simulator expects a modern Verilator 5.x environment. The Makefile defaults
  to `conda run -n step_cv6_test` so it does not pick up the older global
  `VERILATOR_ROOT`.
- The current wrapper keeps the existing synthetic STEP-side load/store behavior,
  while CPU MMIO and DMA source reads flow through the real CV6 cache/memory path.
- The replay flow is still present for quick accelerator-only comparisons.
