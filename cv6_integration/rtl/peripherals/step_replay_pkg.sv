package step_replay_pkg;

  localparam int unsigned STEP_META_BITS = 779;
  localparam int unsigned STEP_BIT_BITS  = 155;
  localparam int unsigned STEP_META_WORDS = (STEP_META_BITS + 31) / 32;
  localparam int unsigned STEP_BIT_WORDS  = (STEP_BIT_BITS + 31) / 32;

  localparam logic [15:0] STEP_MMIO_CTRL_ADDR       = 16'h0000;
  localparam logic [15:0] STEP_MMIO_STATUS_ADDR     = 16'h0004;
  localparam logic [15:0] STEP_MMIO_META_DATA_ADDR  = 16'h0010;
  localparam logic [15:0] STEP_MMIO_META_COMMIT_ADDR= 16'h0014;
  localparam logic [15:0] STEP_MMIO_BIT_DATA_ADDR   = 16'h0018;
  localparam logic [15:0] STEP_MMIO_BIT_COMMIT_ADDR = 16'h001C;
  localparam logic [15:0] STEP_MMIO_DMA_SRC_ADDR    = 16'h0020;
  localparam logic [15:0] STEP_MMIO_DMA_DST_ADDR    = 16'h0024;
  localparam logic [15:0] STEP_MMIO_DMA_LEN_ADDR    = 16'h0028;
  localparam logic [15:0] STEP_MMIO_DMA_CMD_ADDR    = 16'h002C;
  localparam logic [15:0] STEP_MMIO_EXIT_ADDR       = 16'h0030;

  localparam logic [7:0] STEP_CMD_NOP       = 8'h00;
  localparam logic [7:0] STEP_CMD_MMIO_WR   = 8'h01;
  localparam logic [7:0] STEP_CMD_WAIT_DONE = 8'h02;
  localparam logic [7:0] STEP_CMD_FINISH    = 8'hFF;

  localparam logic [31:0] STEP_DMA_CMD_NONE  = 32'h0;
  localparam logic [31:0] STEP_DMA_CMD_META  = 32'h1;
  localparam logic [31:0] STEP_DMA_CMD_BIT   = 32'h2;

endpackage
