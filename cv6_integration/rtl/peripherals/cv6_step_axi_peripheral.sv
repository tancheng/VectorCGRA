module cv6_step_axi_peripheral #(
  parameter int unsigned AXI_ADDR_WIDTH = 64,
  parameter int unsigned AXI_DATA_WIDTH = 64,
  parameter int unsigned AXI_ID_WIDTH   = 4,
  parameter int unsigned AXI_USER_WIDTH = 1
)(
  input  logic clk_i,
  input  logic rst_ni,
  AXI_BUS.Slave slave,
  output logic [31:0] exit_code_o,
  output logic step_done_o,
  output logic dma_mem_valid_o,
  output logic [31:0] dma_mem_addr_o,
  input  logic [31:0] dma_mem_rdata_i,
  output logic [43:0] step_ld_mem_addr_o [0:1],
  input  logic [31:0] step_ld_mem_rdata_i [0:1],
  output logic        step_st_mem_we_o [0:1],
  output logic [43:0] step_st_mem_addr_o [0:1],
  output logic [31:0] step_st_mem_wdata_o [0:1],
  output logic [3:0]  step_st_mem_be_o [0:1]
);

  logic        mmio_valid;
  logic        mmio_write;
  logic [15:0] mmio_addr;
  logic [31:0] mmio_wdata;
  logic [31:0] mmio_rdata;
  logic        aw_pending_q;
  logic [AXI_ID_WIDTH-1:0] aw_id_q;
  logic [AXI_ADDR_WIDTH-1:0] aw_addr_q;
  logic        w_pending_q;
  logic [AXI_DATA_WIDTH-1:0] w_data_q;
  logic [(AXI_DATA_WIDTH/8)-1:0] w_strb_q;
  logic        b_valid_q;
  logic [AXI_ID_WIDTH-1:0] b_id_q;
  logic        r_valid_q;
  logic [AXI_ID_WIDTH-1:0] r_id_q;
  logic [AXI_DATA_WIDTH-1:0] r_data_q;

  assign mmio_valid = (aw_pending_q && w_pending_q && !b_valid_q) || (slave.aw_valid && slave.aw_ready && slave.w_valid && slave.w_ready) ||
                      (slave.ar_valid && slave.ar_ready);
  assign mmio_write = (aw_pending_q && w_pending_q && !b_valid_q) || (slave.aw_valid && slave.aw_ready && slave.w_valid && slave.w_ready);
  assign mmio_addr = mmio_write ? ((aw_pending_q && w_pending_q && !b_valid_q) ? aw_addr_q[15:0] : slave.aw_addr[15:0]) : slave.ar_addr[15:0];
  always_comb begin
    if ((aw_pending_q && w_pending_q && !b_valid_q)) begin
      if (|w_strb_q[7:4] && ~|w_strb_q[3:0]) begin
        mmio_wdata = w_data_q[63:32];
      end else begin
        mmio_wdata = w_data_q[31:0];
      end
    end else if (|slave.w_strb[7:4] && ~|slave.w_strb[3:0]) begin
      mmio_wdata = slave.w_data[63:32];
    end else begin
      mmio_wdata = slave.w_data[31:0];
    end
  end

  always_comb begin
    slave.aw_ready = rst_ni && !aw_pending_q && !b_valid_q;
    slave.w_ready  = rst_ni && !w_pending_q && !b_valid_q;
    slave.b_valid  = b_valid_q;
    slave.b_id     = b_id_q;
    slave.b_resp   = '0;
    slave.b_user   = '0;
    slave.ar_ready = rst_ni && !r_valid_q;
    slave.r_valid  = r_valid_q;
    slave.r_id     = r_id_q;
    slave.r_data   = r_data_q;
    slave.r_resp   = '0;
    slave.r_last   = 1'b1;
    slave.r_user   = '0;
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      aw_pending_q <= 1'b0;
      aw_id_q      <= '0;
      aw_addr_q    <= '0;
      w_pending_q  <= 1'b0;
      w_data_q     <= '0;
      w_strb_q     <= '0;
      b_valid_q    <= 1'b0;
      b_id_q       <= '0;
      r_valid_q    <= 1'b0;
      r_id_q       <= '0;
      r_data_q     <= '0;
    end else begin
      if (slave.aw_valid && slave.aw_ready) begin
        aw_pending_q <= 1'b1;
        aw_id_q      <= slave.aw_id;
        aw_addr_q    <= slave.aw_addr;
      end

      if (slave.w_valid && slave.w_ready) begin
        w_pending_q <= 1'b1;
        w_data_q    <= slave.w_data;
        w_strb_q    <= slave.w_strb;
      end

      if (mmio_write) begin
        aw_pending_q <= 1'b0;
        w_pending_q  <= 1'b0;
        b_valid_q    <= 1'b1;
        b_id_q       <= (aw_pending_q && w_pending_q && !b_valid_q) ? aw_id_q : slave.aw_id;
      end else if (b_valid_q && slave.b_ready) begin
        b_valid_q <= 1'b0;
      end

      if (slave.ar_valid && slave.ar_ready) begin
        r_valid_q <= 1'b1;
        r_id_q    <= slave.ar_id;
        r_data_q  <= {mmio_rdata, mmio_rdata};
      end else if (r_valid_q && slave.r_ready) begin
        r_valid_q <= 1'b0;
      end
    end
  end

  step_mmio_dma_wrapper i_step_wrap (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .mmio_valid_i(mmio_valid),
    .mmio_write_i(mmio_write),
    .mmio_addr_i(mmio_addr),
    .mmio_wdata_i(mmio_wdata),
    .mmio_ready_o(),
    .mmio_rdata_o(mmio_rdata),
    .step_done_o(step_done_o),
    .exit_code_o(exit_code_o),
    .dma_mem_valid_o(dma_mem_valid_o),
    .dma_mem_addr_o(dma_mem_addr_o),
    .dma_mem_rdata_i(dma_mem_rdata_i),
    .step_ld_mem_addr_o(step_ld_mem_addr_o),
    .step_ld_mem_rdata_i(step_ld_mem_rdata_i),
    .step_st_mem_we_o(step_st_mem_we_o),
    .step_st_mem_addr_o(step_st_mem_addr_o),
    .step_st_mem_wdata_o(step_st_mem_wdata_o),
    .step_st_mem_be_o(step_st_mem_be_o)
  );
endmodule
