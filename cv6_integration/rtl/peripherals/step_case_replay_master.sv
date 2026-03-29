module step_case_replay_master
  import step_replay_pkg::*;
#(
  parameter string SCRIPT_HEX = ""
)(
  input  logic        clk_i,
  input  logic        rst_ni,
  output logic        mmio_valid_o,
  output logic        mmio_write_o,
  output logic [15:0] mmio_addr_o,
  output logic [31:0] mmio_wdata_o,
  input  logic        mmio_ready_i,
  input  logic [31:0] mmio_rdata_i,
  input  logic        step_done_i,
  output logic        script_done_o
);

  localparam int unsigned MAX_SCRIPT_WORDS = 4096;

  logic [63:0] script_mem [0:MAX_SCRIPT_WORDS-1];
  logic [11:0] pc_q;
  logic waiting_done_q;
  string script_file;

  initial begin
    if (!$value$plusargs("SCRIPT=%s", script_file)) begin
      script_file = SCRIPT_HEX;
    end
    if (script_file != "") begin
      $readmemh(script_file, script_mem);
    end else begin
      $fatal(1, "step_case_replay_master requires SCRIPT plusarg or SCRIPT_HEX parameter");
    end
  end

  wire [63:0] instr = script_mem[pc_q];
  wire [7:0]  opcode = instr[63:56];
  wire [15:0] addr   = instr[47:32];
  wire [31:0] data   = instr[31:0];

  assign mmio_valid_o = rst_ni && !script_done_o && !waiting_done_q && (opcode == STEP_CMD_MMIO_WR);
  assign mmio_write_o = 1'b1;
  assign mmio_addr_o  = addr;
  assign mmio_wdata_o = data;

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      pc_q <= '0;
      waiting_done_q <= 1'b0;
      script_done_o <= 1'b0;
    end else if (!script_done_o) begin
      if (waiting_done_q) begin
        if (step_done_i) begin
          waiting_done_q <= 1'b0;
          pc_q <= pc_q + 1'b1;
        end
      end else begin
        unique case (opcode)
          STEP_CMD_NOP: pc_q <= pc_q + 1'b1;
          STEP_CMD_MMIO_WR: begin
            if (mmio_ready_i) pc_q <= pc_q + 1'b1;
          end
          STEP_CMD_WAIT_DONE: begin
            waiting_done_q <= 1'b1;
          end
          STEP_CMD_FINISH: begin
            script_done_o <= 1'b1;
          end
          default: begin
            script_done_o <= 1'b1;
          end
        endcase
      end
    end
  end

endmodule
