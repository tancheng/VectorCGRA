CV6_INT_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
STEP_ENV_NAME ?= step_cv6_test
STEP_ENV_PREFIX ?= /data/angl7/bin/miniconda3/envs/$(STEP_ENV_NAME)
PYTEST_ENV_PREFIX ?= /data/angl7/bin/miniconda3/envs/vector_cgra_base
BENCHMARKS_DIR ?= $(CV6_INT_ROOT)/../cgra/test/benchmarks
BENCHMARK_RESULTS_DIR ?= $(CV6_INT_ROOT)/generated/benchmark_batch
BENCHMARK_STANDALONE_MAX_CYCLES ?= 200000
BENCHMARK_LIMIT ?= 0
ifeq ($(CONDA_DEFAULT_ENV),$(STEP_ENV_NAME))
CONDA_RUN ?= env -u VERILATOR_ROOT
else
CONDA_RUN ?= env -u VERILATOR_ROOT conda run -p $(STEP_ENV_PREFIX)
endif
VERILATOR ?= $(CONDA_RUN) verilator
PYTHON ?= $(CONDA_RUN) python
VERILATOR_BUILD_JOBS ?= 16

ARA_ROOT := $(CV6_INT_ROOT)/ara
CVA6_ROOT := $(ARA_ROOT)/hardware/deps/cva6
COREV_APU := $(CVA6_ROOT)/corev_apu
LLVM_BIN := $(ARA_ROOT)/toolchain/riscv-llvm/build/bin
CLANG := $(LLVM_BIN)/clang
OBJCOPY := $(LLVM_BIN)/llvm-objcopy

CPU_TARGET_CFG ?= cv32a6_imac_sv32
CVA6_CORE_FLIST := $(CVA6_ROOT)/core/Flist.cva6
CVA6_FLATTENER := $(CVA6_ROOT)/util/flist_flattener.py

TB_TOP := cv6_step_replay_top
OBJ_DIR := $(CV6_INT_ROOT)/obj_dir
SIM_MAIN := $(CV6_INT_ROOT)/tb/sim_main.cpp

TOP_FILE := $(CV6_INT_ROOT)/rtl/cv6/cv6_step_replay_top.sv
PKG_FILE := $(CV6_INT_ROOT)/rtl/peripherals/step_replay_pkg.sv
REPLAY_FILE := $(CV6_INT_ROOT)/rtl/peripherals/step_case_replay_master.sv
WRAP_FILE := $(CV6_INT_ROOT)/rtl/peripherals/step_mmio_dma_wrapper.sv
STEP_FILE := $(CV6_INT_ROOT)/rtl/step/STEP_CgraRTL__2c9482af1bbb680a__pickled.v

STEP_TB ?= $(CV6_INT_ROOT)/../cgra/test/STEP_CgraRTL__2c9482af1bbb680a_test_all_mappings_dfg_mapping_gemm.json_tb.v
STEP_CASES ?= $(STEP_TB).cases
STEP_NAME_RAW := $(notdir $(basename $(STEP_TB)))
STEP_NAME := $(subst .,_,$(patsubst %_tb,%,$(STEP_NAME_RAW)))
STEP_SCRIPT := $(CV6_INT_ROOT)/generated/$(STEP_NAME)_replay.hex
STEP_HEADER := $(CV6_INT_ROOT)/generated/step_packets.h
ACCEL_CASE_SVH := $(CV6_INT_ROOT)/generated/step_accel_case_model.svh
CPU_ELF := $(CV6_INT_ROOT)/generated/$(STEP_NAME).elf
CPU_BIN := $(CV6_INT_ROOT)/generated/$(STEP_NAME).bin
CPU_MEMH := $(CV6_INT_ROOT)/generated/$(STEP_NAME).memh
CPU_STATS := $(CV6_INT_ROOT)/generated/$(STEP_NAME)_stats.json
CPU_SIM_MAIN := $(CV6_INT_ROOT)/tb/sim_cpu_main.cpp
CPU_FILELIST := $(CV6_INT_ROOT)/generated/cv6_cpu_files.f

EXTRA_INCDIRS := \
	+incdir+$(COREV_APU)/tb \
	+incdir+$(COREV_APU)/bootrom \
	+incdir+$(COREV_APU)/axi_mem_if/src \
	+incdir+$(COREV_APU)/src/axi_riscv_atomics/src \
	+incdir+$(CV6_INT_ROOT)/generated \
	+incdir+$(CV6_INT_ROOT)/rtl/cv6 \
	+incdir+$(CV6_INT_ROOT)/rtl/peripherals \
	+incdir+$(CV6_INT_ROOT)/rtl/step

COMMON_LOCAL_RTL := \
	$(CV6_INT_ROOT)/rtl/peripherals/step_replay_pkg.sv \
	$(CV6_INT_ROOT)/rtl/step/STEP_CgraRTL__2c9482af1bbb680a__pickled.v \
	$(CV6_INT_ROOT)/rtl/peripherals/step_mmio_dma_wrapper.sv \
	$(CV6_INT_ROOT)/rtl/peripherals/cv6_step_dram.sv \
	$(CV6_INT_ROOT)/rtl/peripherals/cv6_step_axi_peripheral.sv \
	$(CV6_INT_ROOT)/rtl/cv6/cv6_step_core_boundary.sv \
	$(CV6_INT_ROOT)/rtl/cv6/cv6_step_testharness.sv

.PHONY: gen_step
gen_step:
	mkdir -p $(CV6_INT_ROOT)/generated
	$(PYTHON) $(CV6_INT_ROOT)/tb/gen_step_replay.py --tb $(STEP_TB) --cases $(STEP_CASES) --out $(STEP_SCRIPT)

.PHONY: sim_replay_step
sim_replay_step: gen_step
	$(VERILATOR) --cc --exe --build --build-jobs $(VERILATOR_BUILD_JOBS) --sv -Wno-WIDTH -Wno-UNSIGNED -Wno-UNOPTFLAT \
	  --top-module $(TB_TOP) \
	  -o V$(TB_TOP) \
	  -Mdir $(OBJ_DIR) \
	  $(PKG_FILE) $(STEP_FILE) $(WRAP_FILE) $(REPLAY_FILE) $(TOP_FILE) $(SIM_MAIN)
	$(OBJ_DIR)/V$(TB_TOP) +SCRIPT=$(STEP_SCRIPT)

.PHONY: force_step_codegen
force_step_codegen:

$(STEP_HEADER): force_step_codegen $(CV6_INT_ROOT)/tb/gen_step_dma_header.py $(STEP_TB) $(STEP_CASES)
	mkdir -p $(CV6_INT_ROOT)/generated
	$(PYTHON) $(CV6_INT_ROOT)/tb/gen_step_dma_header.py --tb $(STEP_TB) --cases $(STEP_CASES) --out $(STEP_HEADER)

$(ACCEL_CASE_SVH): force_step_codegen $(CV6_INT_ROOT)/tb/gen_step_accel_case_model.py $(STEP_TB) $(STEP_CASES)
	mkdir -p $(CV6_INT_ROOT)/generated
	$(PYTHON) $(CV6_INT_ROOT)/tb/gen_step_accel_case_model.py --tb $(STEP_TB) --cases $(STEP_CASES) --out $(ACCEL_CASE_SVH)

.PHONY: gen_cpu_step
gen_cpu_step: $(STEP_HEADER) $(ACCEL_CASE_SVH)

$(CPU_ELF): $(CV6_INT_ROOT)/Makefile $(CV6_INT_ROOT)/sw/start.S $(CV6_INT_ROOT)/sw/step_cpu_main.c $(CV6_INT_ROOT)/sw/link.ld $(STEP_HEADER)
	$(CLANG) --target=riscv32 -march=rv32imac_zicsr -mabi=ilp32 -mcmodel=medany -nostdlib -ffreestanding \
	  -Wl,-T,$(CV6_INT_ROOT)/sw/link.ld -Wl,--no-relax \
	  -I$(CV6_INT_ROOT)/generated \
	  $(CV6_INT_ROOT)/sw/start.S $(CV6_INT_ROOT)/sw/step_cpu_main.c \
	  -o $(CPU_ELF)

$(CPU_BIN): $(CPU_ELF)
	$(OBJCOPY) -O binary $(CPU_ELF) $(CPU_BIN)

$(CPU_MEMH): $(CPU_BIN)
	$(PYTHON) $(CV6_INT_ROOT)/tb/bin_to_mem.py --bin $(CPU_BIN) --out $(CPU_MEMH)

.PHONY: build_cpu_step
build_cpu_step: $(CPU_MEMH) $(ACCEL_CASE_SVH)

$(CPU_FILELIST): $(CV6_INT_ROOT)/Makefile $(CVA6_CORE_FLIST) $(CVA6_FLATTENER)
	mkdir -p $(CV6_INT_ROOT)/generated
	{ \
	  printf '%s\n' $(EXTRA_INCDIRS); \
	  env CVA6_REPO_DIR=$(CVA6_ROOT) TARGET_CFG=$(CPU_TARGET_CFG) HPDCACHE_DIR=$(CVA6_ROOT)/core/cache_subsystem/hpdcache \
	    $(PYTHON) $(CVA6_FLATTENER) --print_incdir --print_newline $(CVA6_CORE_FLIST); \
	  echo "$(COREV_APU)/tb/ariane_soc_pkg.sv"; \
	  echo "$(COREV_APU)/tb/ariane_axi_pkg.sv"; \
	  echo "$(COREV_APU)/tb/ariane_axi_soc_pkg.sv"; \
	  echo "$(COREV_APU)/tb/axi_intf.sv"; \
	  echo "$(COREV_APU)/bootrom/bootrom.sv"; \
	  echo "$(COREV_APU)/axi_mem_if/src/axi2mem.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/common_cells/src/deprecated/fifo_v2.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/axi/src/axi_id_prepend.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/axi/src/axi_atop_filter.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/axi/src/axi_err_slv.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/axi/src/axi_demux.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/axi/src/axi_mux.sv"; \
	  echo "$(CVA6_ROOT)/vendor/pulp-platform/axi/src/axi_xbar.sv"; \
	  echo "$(COREV_APU)/src/axi_riscv_atomics/src/axi_res_tbl.sv"; \
	  echo "$(COREV_APU)/src/axi_riscv_atomics/src/axi_riscv_amos_alu.sv"; \
	  echo "$(COREV_APU)/src/axi_riscv_atomics/src/axi_riscv_amos.sv"; \
	  echo "$(COREV_APU)/src/axi_riscv_atomics/src/axi_riscv_lrsc.sv"; \
	  echo "$(COREV_APU)/src/axi_riscv_atomics/src/axi_riscv_atomics.sv"; \
	  echo "$(COREV_APU)/src/axi_riscv_atomics/src/axi_riscv_atomics_wrap.sv"; \
	  printf '%s\n' $(COMMON_LOCAL_RTL); \
	} > $(CPU_FILELIST)

.PHONY: sim_cv6_step
sim_cv6_step: build_cpu_step $(CPU_FILELIST)
	$(VERILATOR) --cc --exe --build --build-jobs $(VERILATOR_BUILD_JOBS) --sv -Wno-WIDTH -Wno-UNSIGNED -Wno-UNOPTFLAT -Wno-fatal \
	  -DSYNTHESIS \
	  --language 1800-2012 \
	  --top-module cv6_step_testharness \
	  -Mdir $(OBJ_DIR) \
	  -o Vcv6_step_testharness \
	  $(CVA6_ROOT)/verilator_config.vlt \
	  -GDRAM_INIT_FILE=\"$(CPU_MEMH)\" \
	  $(EXTRA_INCDIRS) \
	  -f $(CPU_FILELIST) \
	  $(CPU_SIM_MAIN)
	STEP_STATS_FILE=$(CPU_STATS) $(OBJ_DIR)/Vcv6_step_testharness

.PHONY: sim_cv6_benchmarks
sim_cv6_benchmarks:
	python3 $(CV6_INT_ROOT)/tb/run_step_benchmarks.py \
	  --benchmark-dir $(BENCHMARKS_DIR) \
	  --results-dir $(BENCHMARK_RESULTS_DIR) \
	  --pytest-env-prefix $(PYTEST_ENV_PREFIX) \
	  --cv6-env-prefix $(STEP_ENV_PREFIX) \
	  --standalone-max-cycles $(BENCHMARK_STANDALONE_MAX_CYCLES) \
	  --limit $(BENCHMARK_LIMIT)

.PHONY: gen_gemm
gen_gemm: gen_step

.PHONY: gen_cpu_gemm
gen_cpu_gemm: gen_cpu_step

.PHONY: build_cpu_gemm
build_cpu_gemm: build_cpu_step

.PHONY: sim_cv6_gemm
sim_cv6_gemm: sim_cv6_step

.PHONY: sim_replay
sim_replay: sim_replay_step

.PHONY: clean
clean:
	rm -rf $(OBJ_DIR) $(CV6_INT_ROOT)/generated/*.hex $(CV6_INT_ROOT)/generated/*.h $(CV6_INT_ROOT)/generated/*.elf $(CV6_INT_ROOT)/generated/*.bin $(CV6_INT_ROOT)/generated/*.memh $(CV6_INT_ROOT)/generated/*.f $(BENCHMARK_RESULTS_DIR)
