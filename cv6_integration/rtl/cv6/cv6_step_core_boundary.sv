`include "rvfi_types.svh"
`include "cvxif_types.svh"

module cv6_step_core_boundary
  import ariane_pkg::*;
#(
  parameter config_pkg::cva6_cfg_t CVA6Cfg = build_config_pkg::build_config(cva6_config_pkg::cva6_cfg),
  parameter type rvfi_probes_instr_t = `RVFI_PROBES_INSTR_T(CVA6Cfg),
  parameter type rvfi_probes_csr_t = `RVFI_PROBES_CSR_T(CVA6Cfg),
  parameter type rvfi_probes_t = struct packed {
    rvfi_probes_csr_t csr;
    rvfi_probes_instr_t instr;
  },
  parameter int unsigned AxiAddrWidth = ariane_axi::AddrWidth,
  parameter int unsigned AxiDataWidth = ariane_axi::DataWidth,
  parameter int unsigned AxiIdWidth   = ariane_axi::IdWidth,
  parameter type axi_ar_chan_t = ariane_axi::ar_chan_t,
  parameter type axi_aw_chan_t = ariane_axi::aw_chan_t,
  parameter type axi_w_chan_t  = ariane_axi::w_chan_t,
  parameter type noc_req_t = ariane_axi::req_t,
  parameter type noc_resp_t = ariane_axi::resp_t
)(
  input  logic clk_i,
  input  logic rst_ni,
  input  logic [CVA6Cfg.VLEN-1:0] boot_addr_i,
  input  logic [CVA6Cfg.XLEN-1:0] hart_id_i,
  input  logic [1:0] irq_i,
  input  logic ipi_i,
  input  logic time_irq_i,
  input  logic debug_req_i,
  output rvfi_probes_t rvfi_probes_o,
  output noc_req_t noc_req_o,
  input  noc_resp_t noc_resp_i
);
  localparam type readregflags_t      = `READREGFLAGS_T(CVA6Cfg);
  localparam type writeregflags_t     = `WRITEREGFLAGS_T(CVA6Cfg);
  localparam type id_t                = `ID_T(CVA6Cfg);
  localparam type hartid_t            = `HARTID_T(CVA6Cfg);
  localparam type x_compressed_req_t  = `X_COMPRESSED_REQ_T(CVA6Cfg, hartid_t);
  localparam type x_compressed_resp_t = `X_COMPRESSED_RESP_T(CVA6Cfg);
  localparam type x_issue_req_t       = `X_ISSUE_REQ_T(CVA6Cfg, hartid_t, id_t);
  localparam type x_issue_resp_t      = `X_ISSUE_RESP_T(CVA6Cfg, writeregflags_t, readregflags_t);
  localparam type x_register_t        = `X_REGISTER_T(CVA6Cfg, hartid_t, id_t, readregflags_t);
  localparam type x_commit_t          = `X_COMMIT_T(CVA6Cfg, hartid_t, id_t);
  localparam type x_result_t          = `X_RESULT_T(CVA6Cfg, hartid_t, id_t, writeregflags_t);
  localparam type cvxif_req_t         = `CVXIF_REQ_T(CVA6Cfg, x_compressed_req_t, x_issue_req_t, x_register_t, x_commit_t);
  localparam type cvxif_resp_t        = `CVXIF_RESP_T(CVA6Cfg, x_compressed_resp_t, x_issue_resp_t, x_result_t);

  cvxif_req_t cvxif_req_unused;
  cvxif_resp_t cvxif_resp_tied;

  assign cvxif_resp_tied = '0;

  cva6 #(
    .CVA6Cfg ( CVA6Cfg ),
    .rvfi_probes_instr_t ( rvfi_probes_instr_t ),
    .rvfi_probes_csr_t ( rvfi_probes_csr_t ),
    .rvfi_probes_t ( rvfi_probes_t ),
    .axi_ar_chan_t ( axi_ar_chan_t ),
    .axi_aw_chan_t ( axi_aw_chan_t ),
    .axi_w_chan_t ( axi_w_chan_t ),
    .noc_req_t ( noc_req_t ),
    .noc_resp_t ( noc_resp_t ),
    .readregflags_t ( readregflags_t ),
    .writeregflags_t ( writeregflags_t ),
    .id_t ( id_t ),
    .hartid_t ( hartid_t ),
    .x_compressed_req_t ( x_compressed_req_t ),
    .x_compressed_resp_t ( x_compressed_resp_t ),
    .x_issue_req_t ( x_issue_req_t ),
    .x_issue_resp_t ( x_issue_resp_t ),
    .x_register_t ( x_register_t ),
    .x_commit_t ( x_commit_t ),
    .x_result_t ( x_result_t ),
    .cvxif_req_t ( cvxif_req_t ),
    .cvxif_resp_t ( cvxif_resp_t )
  ) i_cva6 (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .boot_addr_i(boot_addr_i),
    .hart_id_i(hart_id_i),
    .irq_i(irq_i),
    .ipi_i(ipi_i),
    .time_irq_i(time_irq_i),
    .debug_req_i(debug_req_i),
    .clic_irq_valid_i(1'b0),
    .clic_irq_id_i('0),
    .clic_irq_level_i('0),
    .clic_irq_priv_i(riscv::PRIV_LVL_M),
    .clic_irq_shv_i(1'b0),
    .clic_irq_ready_o(),
    .clic_kill_req_i(1'b0),
    .clic_kill_ack_o(),
    .rvfi_probes_o(rvfi_probes_o),
    .cvxif_req_o(cvxif_req_unused),
    .cvxif_resp_i(cvxif_resp_tied),
    .noc_req_o(noc_req_o),
    .noc_resp_i(noc_resp_i)
  );

endmodule
