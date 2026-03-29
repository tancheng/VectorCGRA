module cv6_step_dram #(
  parameter int unsigned ADDR_WIDTH = 64,
  parameter int unsigned DATA_WIDTH = 64,
  parameter int unsigned USER_WIDTH = 1,
  parameter int unsigned NUM_WORDS  = 16384,
  parameter logic [ADDR_WIDTH-1:0] BASE_ADDR = 64'h8000_0000,
  parameter string INIT_FILE = ""
)(
  input  logic clk_i,
  input  logic rst_ni,

  input  logic req_i,
  input  logic we_i,
  input  logic [ADDR_WIDTH-1:0] addr_i,
  input  logic [USER_WIDTH-1:0] wuser_i,
  input  logic [DATA_WIDTH-1:0] wdata_i,
  input  logic [(DATA_WIDTH/8)-1:0] be_i,
  output logic [USER_WIDTH-1:0] ruser_o,
  output logic [DATA_WIDTH-1:0] rdata_o,

  input  logic dma_rd_valid_i,
  input  logic [31:0] dma_rd_addr_i,
  output logic [31:0] dma_rd_data_o,

  input  logic [43:0] step_ld_addr_i [0:1],
  output logic [31:0] step_ld_data_o [0:1],
  input  logic        step_st_we_i [0:1],
  input  logic [43:0] step_st_addr_i [0:1],
  input  logic [31:0] step_st_wdata_i [0:1],
  input  logic [3:0]  step_st_be_i [0:1]
);

  localparam int unsigned WORD_SHIFT = $clog2(DATA_WIDTH/8);
  localparam int unsigned INDEX_WIDTH = $clog2(NUM_WORDS);
  logic [DATA_WIDTH-1:0] mem [0:NUM_WORDS-1];
  logic [ADDR_WIDTH-1:0] addr_q;
  logic [ADDR_WIDTH-1:0] local_addr_q;
  logic [ADDR_WIDTH-1:0] wr_local_addr;
  logic [INDEX_WIDTH-1:0] rd_idx;
  logic [INDEX_WIDTH-1:0] wr_idx;
  logic [31:0] dma_local_addr;
  logic [INDEX_WIDTH-1:0] dma_idx;
  logic [43:0] step_ld_local_addr [0:1];
  logic [INDEX_WIDTH-1:0] step_ld_idx [0:1];
  logic [43:0] step_st_local_addr [0:1];
  logic [INDEX_WIDTH-1:0] step_st_idx [0:1];
  integer debug_access_count;
  integer i;

  assign wr_local_addr = addr_i - BASE_ADDR;
  assign wr_idx = wr_local_addr[WORD_SHIFT +: INDEX_WIDTH];
  assign rd_idx = local_addr_q[WORD_SHIFT +: INDEX_WIDTH];
  assign dma_local_addr = dma_rd_addr_i - BASE_ADDR[31:0];
  assign dma_idx = dma_local_addr[WORD_SHIFT +: INDEX_WIDTH];

  generate
    for (genvar p = 0; p < 2; p++) begin : gen_step_mem_idx
      assign step_ld_local_addr[p] = step_ld_addr_i[p] - BASE_ADDR[43:0];
      assign step_ld_idx[p] = step_ld_local_addr[p][WORD_SHIFT +: INDEX_WIDTH];
      assign step_st_local_addr[p] = step_st_addr_i[p] - BASE_ADDR[43:0];
      assign step_st_idx[p] = step_st_local_addr[p][WORD_SHIFT +: INDEX_WIDTH];
    end
  endgenerate

  initial begin
    for (i = 0; i < NUM_WORDS; i++) begin
      mem[i] = '0;
    end
    if (INIT_FILE != "") begin
      $readmemh(INIT_FILE, mem);
    end
    debug_access_count = 0;
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      addr_q <= '0;
      local_addr_q <= '0;
      debug_access_count <= 0;
    end else begin
      if (req_i) begin
        addr_q <= addr_i;
        local_addr_q <= addr_i - BASE_ADDR;
        if (debug_access_count < 16) begin
          $display("[cv6_step_dram] req we=%0d addr=%08x wdata=%016x", we_i, addr_i, wdata_i);
          debug_access_count <= debug_access_count + 1;
        end
        if (we_i) begin
          for (int b = 0; b < DATA_WIDTH/8; b++) begin
            if (be_i[b]) begin
              mem[wr_idx][8*b +: 8] <= wdata_i[8*b +: 8];
            end
          end
        end
      end

      for (int p = 0; p < 2; p++) begin
        if (step_st_we_i[p]) begin
          for (int b = 0; b < 4; b++) begin
            if (step_st_be_i[p][b]) begin
              mem[step_st_idx[p]][8*b +: 8] <= step_st_wdata_i[p][8*b +: 8];
            end
          end
        end
      end
    end
  end

  assign rdata_o = mem[rd_idx];
  assign ruser_o = wuser_i;

  generate
    for (genvar p = 0; p < 2; p++) begin : gen_step_reads
      assign step_ld_data_o[p] = mem[step_ld_idx[p]][31:0];
    end
  endgenerate

  always_comb begin
    dma_rd_data_o = 32'd0;
    if (dma_rd_valid_i) begin
      logic [DATA_WIDTH-1:0] word;
      word = mem[dma_idx];
      dma_rd_data_o = dma_rd_addr_i[2] ? word[63:32] : word[31:0];
    end
  end
endmodule
