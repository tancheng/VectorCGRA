`include "axi/assign.svh"

module cv6_step_testharness #(
  parameter config_pkg::cva6_cfg_t CVA6Cfg = build_config_pkg::build_config(cva6_config_pkg::cva6_cfg),
  parameter int unsigned AXI_USER_WIDTH    = CVA6Cfg.AxiUserWidth,
  parameter int unsigned AXI_ADDRESS_WIDTH = 64,
  parameter int unsigned AXI_DATA_WIDTH    = 64,
  parameter int unsigned NUM_WORDS         = 16384,
  parameter string DRAM_INIT_FILE          = ""
)(
  input  logic clk_i,
  input  logic rst_ni,
  output logic [31:0] exit_o,
  output logic        step_done_dbg_o,
  output logic [63:0] benchmark_cycle_dbg_o,
  output logic [63:0] first_dma_program_cycle_dbg_o,
  output logic [63:0] first_dma_issue_cycle_dbg_o,
  output logic [63:0] first_dma_stream_cycle_dbg_o,
  output logic [63:0] last_dma_stream_cycle_dbg_o,
  output logic [63:0] first_cgra_metadata_cycle_dbg_o,
  output logic [63:0] last_cgra_metadata_cycle_dbg_o,
  output logic [63:0] first_cgra_bitstream_cycle_dbg_o,
  output logic [63:0] last_cgra_bitstream_cycle_dbg_o,
  output logic [63:0] first_cgra_activity_cycle_dbg_o,
  output logic [63:0] cgra_done_cycle_dbg_o,
  output logic [31:0] dma_transfer_count_dbg_o,
  output logic        dma_transfer_overflow_dbg_o,
  output logic [31:0] dma_transfer_kind_dbg_o [0:255],
  output logic [31:0] dma_transfer_src_dbg_o [0:255],
  output logic [31:0] dma_transfer_len_dbg_o [0:255],
  output logic [63:0] dma_transfer_issue_cycle_dbg_o [0:255],
  output logic [63:0] dma_transfer_start_cycle_dbg_o [0:255],
  output logic [63:0] dma_transfer_end_cycle_dbg_o [0:255],
  output logic [31:0] dma_transfer_words_streamed_dbg_o [0:255]
);

  localparam [7:0] hart_id = '0;
  logic [CVA6Cfg.XLEN-1:0] hart_id_i;
  logic [CVA6Cfg.VLEN-1:0] boot_addr_i;

  always_comb begin
    hart_id_i = '0;
    hart_id_i[7:0] = hart_id;
    boot_addr_i = ariane_soc::DRAMBase[CVA6Cfg.VLEN-1:0];
  end

  AXI_BUS #(
    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH       ),
    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH          ),
    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidth ),
    .AXI_USER_WIDTH ( AXI_USER_WIDTH          )
  ) slave[ariane_soc::NrSlaves-1:0]();

  AXI_BUS #(
    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH            ),
    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH               ),
    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidthSlave ),
    .AXI_USER_WIDTH ( AXI_USER_WIDTH               )
  ) master[ariane_soc::NB_PERIPHERALS-1:0]();

  ariane_axi::req_t axi_ariane_req;
  ariane_axi::resp_t axi_ariane_resp;

  logic [31:0] step_exit_code;
  logic step_done;
  logic dma_mem_valid;
  logic [31:0] dma_mem_addr;
  logic [31:0] dma_mem_rdata;
  logic [43:0] step_ld_mem_addr [0:1];
  logic [31:0] step_ld_mem_rdata [0:1];
  logic        step_st_mem_we [0:1];
  logic [43:0] step_st_mem_addr [0:1];
  logic [31:0] step_st_mem_wdata [0:1];
  logic [3:0]  step_st_mem_be [0:1];

  logic rom_req;
  logic [AXI_ADDRESS_WIDTH-1:0] rom_addr;
  logic [AXI_DATA_WIDTH-1:0] rom_rdata;

  logic req;
  logic we;
  logic [AXI_ADDRESS_WIDTH-1:0] addr;
  logic [AXI_DATA_WIDTH/8-1:0] be;
  logic [AXI_DATA_WIDTH-1:0] wdata;
  logic [AXI_DATA_WIDTH-1:0] rdata;
  logic [AXI_USER_WIDTH-1:0] wuser;
  logic [AXI_USER_WIDTH-1:0] ruser;

  AXI_BUS #(
    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH            ),
    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH               ),
    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidthSlave ),
    .AXI_USER_WIDTH ( AXI_USER_WIDTH               )
  ) dram();

  // Core
  cv6_step_core_boundary #(
    .CVA6Cfg              ( CVA6Cfg             ),
    .noc_req_t            ( ariane_axi::req_t   ),
    .noc_resp_t           ( ariane_axi::resp_t  )
  ) i_cv6 (
    .clk_i                ( clk_i               ),
    .rst_ni               ( rst_ni              ),
    .boot_addr_i          ( boot_addr_i         ),
    .hart_id_i            ( hart_id_i           ),
    .irq_i                ( 2'b00               ),
    .ipi_i                ( 1'b0                ),
    .time_irq_i           ( 1'b0                ),
    .rvfi_probes_o        (                     ),
    .debug_req_i          ( 1'b0                ),
    .noc_req_o            ( axi_ariane_req      ),
    .noc_resp_i           ( axi_ariane_resp     )
  );

  `AXI_ASSIGN_FROM_REQ(slave[0], axi_ariane_req)
  `AXI_ASSIGN_TO_RESP(axi_ariane_resp, slave[0])

  // Tie off second slave port with error responses by leaving it idle.
  assign slave[1].aw_valid = 1'b0;
  assign slave[1].w_valid  = 1'b0;
  assign slave[1].ar_valid = 1'b0;
  assign slave[1].b_ready  = 1'b0;
  assign slave[1].r_ready  = 1'b0;

  // ROM
  axi2mem #(
    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidthSlave ),
    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH            ),
    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH               ),
    .AXI_USER_WIDTH ( AXI_USER_WIDTH               )
  ) i_axi2rom (
    .clk_i  ( clk_i                   ),
    .rst_ni ( rst_ni                  ),
    .slave  ( master[ariane_soc::ROM] ),
    .req_o  ( rom_req                 ),
    .we_o   (                         ),
    .addr_o ( rom_addr                ),
    .be_o   (                         ),
    .user_o (                         ),
    .data_o (                         ),
    .user_i ( '0                      ),
    .data_i ( rom_rdata               )
  );

  bootrom i_bootrom (
    .clk_i   ( clk_i    ),
    .req_i   ( rom_req  ),
    .addr_i  ( rom_addr ),
    .rdata_o ( rom_rdata)
  );

  // DRAM
  axi_riscv_atomics_wrap #(
    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH            ),
    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH               ),
    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidthSlave ),
    .AXI_USER_WIDTH ( AXI_USER_WIDTH               ),
    .AXI_MAX_WRITE_TXNS ( 1 ),
    .RISCV_WORD_WIDTH   ( CVA6Cfg.XLEN )
  ) i_axi_riscv_atomics (
    .clk_i,
    .rst_ni ( rst_ni                    ),
    .slv    ( master[ariane_soc::DRAM]  ),
    .mst    ( dram                      )
  );

  axi2mem #(
    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidthSlave ),
    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH            ),
    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH               ),
    .AXI_USER_WIDTH ( AXI_USER_WIDTH               )
  ) i_axi2mem (
    .clk_i  ( clk_i ),
    .rst_ni ( rst_ni ),
    .slave  ( dram ),
    .req_o  ( req ),
    .we_o   ( we ),
    .addr_o ( addr ),
    .be_o   ( be ),
    .user_o ( wuser ),
    .data_o ( wdata ),
    .user_i ( ruser ),
    .data_i ( rdata )
  );

  cv6_step_dram #(
    .ADDR_WIDTH(AXI_ADDRESS_WIDTH),
    .DATA_WIDTH(AXI_DATA_WIDTH),
    .USER_WIDTH(AXI_USER_WIDTH),
    .NUM_WORDS(NUM_WORDS),
    .INIT_FILE(DRAM_INIT_FILE)
  ) i_dram (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .req_i(req),
    .we_i(we),
    .addr_i(addr),
    .wuser_i(wuser),
    .wdata_i(wdata),
    .be_i(be),
    .ruser_o(ruser),
    .rdata_o(rdata),
    .dma_rd_valid_i(dma_mem_valid),
    .dma_rd_addr_i(dma_mem_addr),
    .dma_rd_data_o(dma_mem_rdata),
    .step_ld_addr_i(step_ld_mem_addr),
    .step_ld_data_o(step_ld_mem_rdata),
    .step_st_we_i(step_st_mem_we),
    .step_st_addr_i(step_st_mem_addr),
    .step_st_wdata_i(step_st_mem_wdata),
    .step_st_be_i(step_st_mem_be)
  );

  // STEP peripheral at GPIO base.
  cv6_step_axi_peripheral #(
    .AXI_ADDR_WIDTH(AXI_ADDRESS_WIDTH),
    .AXI_DATA_WIDTH(AXI_DATA_WIDTH),
    .AXI_ID_WIDTH(ariane_axi_soc::IdWidthSlave),
    .AXI_USER_WIDTH(AXI_USER_WIDTH)
  ) i_step_periph (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .slave(master[ariane_soc::GPIO]),
    .exit_code_o(step_exit_code),
    .step_done_o(step_done),
    .dma_mem_valid_o(dma_mem_valid),
    .dma_mem_addr_o(dma_mem_addr),
    .dma_mem_rdata_i(dma_mem_rdata),
    .benchmark_cycle_dbg_o(benchmark_cycle_dbg_o),
    .first_dma_program_cycle_dbg_o(first_dma_program_cycle_dbg_o),
    .first_dma_issue_cycle_dbg_o(first_dma_issue_cycle_dbg_o),
    .first_dma_stream_cycle_dbg_o(first_dma_stream_cycle_dbg_o),
    .last_dma_stream_cycle_dbg_o(last_dma_stream_cycle_dbg_o),
    .first_cgra_metadata_cycle_dbg_o(first_cgra_metadata_cycle_dbg_o),
    .last_cgra_metadata_cycle_dbg_o(last_cgra_metadata_cycle_dbg_o),
    .first_cgra_bitstream_cycle_dbg_o(first_cgra_bitstream_cycle_dbg_o),
    .last_cgra_bitstream_cycle_dbg_o(last_cgra_bitstream_cycle_dbg_o),
    .first_cgra_activity_cycle_dbg_o(first_cgra_activity_cycle_dbg_o),
    .cgra_done_cycle_dbg_o(cgra_done_cycle_dbg_o),
    .dma_transfer_count_dbg_o(dma_transfer_count_dbg_o),
    .dma_transfer_overflow_dbg_o(dma_transfer_overflow_dbg_o),
    .dma_transfer_kind_dbg_o(dma_transfer_kind_dbg_o),
    .dma_transfer_src_dbg_o(dma_transfer_src_dbg_o),
    .dma_transfer_len_dbg_o(dma_transfer_len_dbg_o),
    .dma_transfer_issue_cycle_dbg_o(dma_transfer_issue_cycle_dbg_o),
    .dma_transfer_start_cycle_dbg_o(dma_transfer_start_cycle_dbg_o),
    .dma_transfer_end_cycle_dbg_o(dma_transfer_end_cycle_dbg_o),
    .dma_transfer_words_streamed_dbg_o(dma_transfer_words_streamed_dbg_o),
    .step_ld_mem_addr_o(step_ld_mem_addr),
    .step_ld_mem_rdata_i(step_ld_mem_rdata),
    .step_st_mem_we_o(step_st_mem_we),
    .step_st_mem_addr_o(step_st_mem_addr),
    .step_st_mem_wdata_o(step_st_mem_wdata),
    .step_st_mem_be_o(step_st_mem_be)
  );

  // Unused peripherals as error slaves.
  for (genvar idx = 0; idx < ariane_soc::NB_PERIPHERALS; idx++) begin : gen_err
    if ((idx != ariane_soc::ROM) && (idx != ariane_soc::DRAM) && (idx != ariane_soc::GPIO)) begin : gen_err_slv
      ariane_axi_soc::req_slv_t req_slv;
      ariane_axi_soc::resp_slv_t resp_slv;
      `AXI_ASSIGN_TO_REQ(req_slv, master[idx])
      `AXI_ASSIGN_FROM_RESP(master[idx], resp_slv)
      axi_err_slv #(
        .AxiIdWidth ( ariane_axi_soc::IdWidthSlave ),
        .req_t      ( ariane_axi_soc::req_slv_t    ),
        .resp_t     ( ariane_axi_soc::resp_slv_t   )
      ) i_err (
        .clk_i      ( clk_i ),
        .rst_ni     ( rst_ni ),
        .test_i     ( 1'b0 ),
        .slv_req_i  ( req_slv ),
        .slv_resp_o ( resp_slv )
      );
    end
  end

  axi_pkg::xbar_rule_64_t [ariane_soc::NB_PERIPHERALS-1:0] addr_map;
  assign addr_map = '{
    '{ idx: ariane_soc::Debug,    start_addr: ariane_soc::DebugBase,    end_addr: ariane_soc::DebugBase + ariane_soc::DebugLength       },
    '{ idx: ariane_soc::ROM,      start_addr: ariane_soc::ROMBase,      end_addr: ariane_soc::ROMBase + ariane_soc::ROMLength           },
    '{ idx: ariane_soc::CLINT,    start_addr: ariane_soc::CLINTBase,    end_addr: ariane_soc::CLINTBase + ariane_soc::CLINTLength       },
    '{ idx: ariane_soc::PLIC,     start_addr: ariane_soc::PLICBase,     end_addr: ariane_soc::PLICBase + ariane_soc::PLICLength         },
    '{ idx: ariane_soc::UART,     start_addr: ariane_soc::UARTBase,     end_addr: ariane_soc::UARTBase + ariane_soc::UARTLength         },
    '{ idx: ariane_soc::Timer,    start_addr: ariane_soc::TimerBase,    end_addr: ariane_soc::TimerBase + ariane_soc::TimerLength       },
    '{ idx: ariane_soc::SPI,      start_addr: ariane_soc::SPIBase,      end_addr: ariane_soc::SPILength + ariane_soc::SPIBase           },
    '{ idx: ariane_soc::Ethernet, start_addr: ariane_soc::EthernetBase, end_addr: ariane_soc::EthernetBase + ariane_soc::EthernetLength },
    '{ idx: ariane_soc::GPIO,     start_addr: ariane_soc::GPIOBase,     end_addr: ariane_soc::GPIOBase + ariane_soc::GPIOLength         },
    '{ idx: ariane_soc::DRAM,     start_addr: ariane_soc::DRAMBase,     end_addr: ariane_soc::DRAMBase + ariane_soc::DRAMLength         }
  };

  localparam axi_pkg::xbar_cfg_t AXI_XBAR_CFG = '{
    NoSlvPorts: unsigned'(ariane_soc::NrSlaves),
    NoMstPorts: unsigned'(ariane_soc::NB_PERIPHERALS),
    MaxMstTrans: unsigned'(1),
    MaxSlvTrans: unsigned'(1),
    FallThrough: 1'b0,
    LatencyMode: axi_pkg::NO_LATENCY,
    AxiIdWidthSlvPorts: unsigned'(ariane_axi_soc::IdWidth),
    AxiIdUsedSlvPorts: unsigned'(ariane_axi_soc::IdWidth),
    UniqueIds: 1'b0,
    AxiAddrWidth: unsigned'(AXI_ADDRESS_WIDTH),
    AxiDataWidth: unsigned'(AXI_DATA_WIDTH),
    NoAddrRules: unsigned'(ariane_soc::NB_PERIPHERALS)
  };

  axi_xbar_intf #(
    .AXI_USER_WIDTH ( AXI_USER_WIDTH          ),
    .Cfg            ( AXI_XBAR_CFG            ),
    .rule_t         ( axi_pkg::xbar_rule_64_t )
  ) i_axi_xbar (
    .clk_i                 ( clk_i      ),
    .rst_ni                ( rst_ni     ),
    .test_i                ( 1'b0       ),
    .slv_ports             ( slave      ),
    .mst_ports             ( master     ),
    .addr_map_i            ( addr_map   ),
    .en_default_mst_port_i ( '0         ),
    .default_mst_port_i    ( '0         )
  );

  assign exit_o = step_exit_code;
  assign step_done_dbg_o = step_done;
endmodule
