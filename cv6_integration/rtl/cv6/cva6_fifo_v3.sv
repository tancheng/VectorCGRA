// Local copy of cva6_fifo_v3 with unsupported assertion syntax removed for
// the older Verilator available in this workspace.
module cva6_fifo_v3 #(
    parameter bit FALL_THROUGH = 1'b0,
    parameter bit FPGA_ALTERA = 1'b0,
    parameter int unsigned DATA_WIDTH = 32,
    parameter int unsigned DEPTH = 8,
    parameter type dtype = logic [DATA_WIDTH-1:0],
    parameter bit FPGA_EN = 1'b0,
    parameter int unsigned ADDR_DEPTH = (DEPTH > 1) ? $clog2(DEPTH) : 1
) (
    input  logic                  clk_i,
    input  logic                  rst_ni,
    input  logic                  flush_i,
    input  logic                  testmode_i,
    output logic                  full_o,
    output logic                  empty_o,
    output logic [ADDR_DEPTH-1:0] usage_o,
    input  dtype                  data_i,
    input  logic                  push_i,
    output dtype                  data_o,
    input  logic                  pop_i
);
  localparam int unsigned FifoDepth = (DEPTH > 0) ? DEPTH : 1;

  logic gate_clock;
  logic [ADDR_DEPTH - 1:0] read_pointer_n, read_pointer_q, write_pointer_n, write_pointer_q;
  logic [ADDR_DEPTH:0] status_cnt_n, status_cnt_q;
  dtype [FifoDepth - 1:0] mem_n, mem_q;
  dtype data_ft_n, data_ft_q;
  logic first_word_n, first_word_q;

  logic fifo_ram_we;
  logic [ADDR_DEPTH-1:0] fifo_ram_read_address;
  logic [ADDR_DEPTH-1:0] fifo_ram_write_address;
  logic [$bits(dtype)-1:0] fifo_ram_wdata;
  logic [$bits(dtype)-1:0] fifo_ram_rdata;

  assign usage_o = status_cnt_q[ADDR_DEPTH-1:0];

  if (DEPTH == 0) begin : gen_pass_through
    assign empty_o = ~push_i;
    assign full_o  = ~pop_i;
  end else begin : gen_fifo
    assign full_o  = (status_cnt_q == FifoDepth[ADDR_DEPTH:0]);
    assign empty_o = (status_cnt_q == 0) & ~(FALL_THROUGH & push_i);
  end

  always_comb begin : read_write_comb
    read_pointer_n  = read_pointer_q;
    write_pointer_n = write_pointer_q;
    status_cnt_n    = status_cnt_q;
    if (FPGA_EN && FPGA_ALTERA) data_ft_n = data_ft_q;
    if (FPGA_EN && FPGA_ALTERA) first_word_n = first_word_q;
    if (FPGA_EN) begin
      fifo_ram_we            = '0;
      fifo_ram_write_address = '0;
      fifo_ram_wdata         = '0;
      if (DEPTH == 0) begin
        data_o = data_i;
      end else begin
        if (FPGA_ALTERA) data_o = first_word_q ? data_ft_q : fifo_ram_rdata;
        else data_o = fifo_ram_rdata;
      end
    end else begin
      data_o     = (DEPTH == 0) ? data_i : mem_q[read_pointer_q];
      mem_n      = mem_q;
      gate_clock = 1'b1;
    end

    if (push_i && ~full_o) begin
      if (FPGA_EN) begin
        fifo_ram_we = 1'b1;
        fifo_ram_write_address = write_pointer_q;
        fifo_ram_wdata = data_i;
        if (FPGA_ALTERA) first_word_n = first_word_q && pop_i;
      end else begin
        mem_n[write_pointer_q] = data_i;
        gate_clock = 1'b0;
      end

      if (write_pointer_q == FifoDepth[ADDR_DEPTH-1:0] - 1) write_pointer_n = '0;
      else write_pointer_n = write_pointer_q + 1;
      status_cnt_n = status_cnt_q + 1;
    end

    if (pop_i && ~empty_o) begin
      data_ft_n = data_i;
      if (FPGA_EN && FPGA_ALTERA) first_word_n = first_word_q && push_i;
      if (read_pointer_n == FifoDepth[ADDR_DEPTH-1:0] - 1) read_pointer_n = '0;
      else read_pointer_n = read_pointer_q + 1;
      status_cnt_n = status_cnt_q - 1;
    end

    if (push_i && pop_i && ~full_o && ~empty_o) status_cnt_n = status_cnt_q;

    if ((FALL_THROUGH || (FPGA_EN && FPGA_ALTERA)) && (status_cnt_q == 0) && push_i) begin
      if (FALL_THROUGH) data_o = data_i;
      if (FPGA_EN && FPGA_ALTERA) begin
        data_ft_n = data_i;
        first_word_n = '1;
      end
      if (pop_i) begin
        first_word_n = '0;
        status_cnt_n = status_cnt_q;
        read_pointer_n = read_pointer_q;
        write_pointer_n = write_pointer_q;
      end
    end

    if (FPGA_EN) fifo_ram_read_address = (FPGA_ALTERA == 1) ? read_pointer_n : read_pointer_q;
    else fifo_ram_read_address = '0;
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (~rst_ni) begin
      read_pointer_q  <= '0;
      write_pointer_q <= '0;
      status_cnt_q    <= '0;
      if (FPGA_ALTERA) first_word_q <= '0;
      if (FPGA_ALTERA) data_ft_q <= '0;
    end else begin
      if (flush_i) begin
        read_pointer_q  <= '0;
        write_pointer_q <= '0;
        status_cnt_q    <= '0;
        if (FPGA_ALTERA) first_word_q <= '0;
        if (FPGA_ALTERA) data_ft_q <= '0;
      end else begin
        read_pointer_q  <= read_pointer_n;
        write_pointer_q <= write_pointer_n;
        status_cnt_q    <= status_cnt_n;
        if (FPGA_ALTERA) data_ft_q <= data_ft_n;
        if (FPGA_ALTERA) first_word_q <= first_word_n;
      end
    end
  end

  if (FPGA_EN) begin : gen_fpga_queue
    if (FPGA_ALTERA) begin
      SyncDpRam_ind_r_w #(
          .ADDR_WIDTH(ADDR_DEPTH),
          .DATA_DEPTH(DEPTH),
          .DATA_WIDTH($bits(dtype))
      ) fifo_ram (
          .Clk_CI   (clk_i),
          .WrEn_SI  (fifo_ram_we),
          .RdAddr_DI(fifo_ram_read_address),
          .WrAddr_DI(fifo_ram_write_address),
          .WrData_DI(fifo_ram_wdata),
          .RdData_DO(fifo_ram_rdata)
      );
    end else begin
      AsyncDpRam #(
          .ADDR_WIDTH(ADDR_DEPTH),
          .DATA_DEPTH(DEPTH),
          .DATA_WIDTH($bits(dtype))
      ) fifo_ram (
          .Clk_CI   (clk_i),
          .WrEn_SI  (fifo_ram_we),
          .RdAddr_DI(fifo_ram_read_address),
          .WrAddr_DI(fifo_ram_write_address),
          .WrData_DI(fifo_ram_wdata),
          .RdData_DO(fifo_ram_rdata)
      );
    end
  end else begin : gen_asic_queue
    always_ff @(posedge clk_i or negedge rst_ni) begin
      if (~rst_ni) begin
        mem_q <= '0;
      end else if (!gate_clock) begin
        mem_q <= mem_n;
      end
    end
  end
endmodule
