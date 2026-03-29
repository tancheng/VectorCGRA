module cv6_step_replay_top
  import step_replay_pkg::*;
#(
  parameter string SCRIPT_HEX = ""
)(
  input logic clk_i,
  input logic rst_ni,
  output logic done_o
);

  logic        mmio_valid;
  logic        mmio_write;
  logic [15:0] mmio_addr;
  logic [31:0] mmio_wdata;
  logic        mmio_ready;
  logic [31:0] mmio_rdata;
  logic        step_done;
  logic        script_done;

  step_case_replay_master #(
    .SCRIPT_HEX(SCRIPT_HEX)
  ) i_replay (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .mmio_valid_o(mmio_valid),
    .mmio_write_o(mmio_write),
    .mmio_addr_o(mmio_addr),
    .mmio_wdata_o(mmio_wdata),
    .mmio_ready_i(mmio_ready),
    .mmio_rdata_i(mmio_rdata),
    .step_done_i(step_done),
    .script_done_o(script_done)
  );

  step_mmio_dma_wrapper i_step_wrapper (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .mmio_valid_i(mmio_valid),
    .mmio_write_i(mmio_write),
    .mmio_addr_i(mmio_addr),
    .mmio_wdata_i(mmio_wdata),
    .mmio_ready_o(mmio_ready),
    .mmio_rdata_o(mmio_rdata),
    .step_done_o(step_done)
  );

  assign done_o = script_done;

endmodule
