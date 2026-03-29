// Local behavioral replacement for tc_sram. This keeps the cache hierarchy
// runnable under the older Verilator in this workspace.
module tc_sram #(
  parameter int unsigned NumWords     = 32'd1024,
  parameter int unsigned DataWidth    = 32'd128,
  parameter int unsigned ByteWidth    = 32'd8,
  parameter int unsigned NumPorts     = 32'd2,
  parameter int unsigned Latency      = 32'd1,
  parameter              SimInit      = "none",
  parameter bit          PrintSimCfg  = 1'b0,
  parameter              ImplKey      = "none",
  parameter int unsigned AddrWidth = (NumWords > 32'd1) ? $clog2(NumWords) : 32'd1,
  parameter int unsigned BeWidth   = (DataWidth + ByteWidth - 32'd1) / ByteWidth,
  parameter type         addr_t    = logic [AddrWidth-1:0],
  parameter type         data_t    = logic [DataWidth-1:0],
  parameter type         be_t      = logic [BeWidth-1:0]
) (
  input  logic                 clk_i,
  input  logic                 rst_ni,
  input  logic  [NumPorts-1:0] req_i,
  input  logic  [NumPorts-1:0] we_i,
  input  addr_t [NumPorts-1:0] addr_i,
  input  data_t [NumPorts-1:0] wdata_i,
  input  be_t   [NumPorts-1:0] be_i,
  output data_t [NumPorts-1:0] rdata_o
);
  localparam int unsigned EffLatency = (Latency == 0) ? 1 : Latency;

  data_t mem [0:NumWords-1];
  data_t rpipe_q [0:NumPorts-1][0:EffLatency-1];
  addr_t r_addr_q [0:NumPorts-1];

  integer i;
  integer p;
  integer l;

  initial begin
    for (i = 0; i < NumWords; i++) begin
      if (SimInit == "ones") mem[i] = '1;
      else mem[i] = '0;
    end
  end

  genvar g;
  generate
    for (g = 0; g < NumPorts; g++) begin : gen_rdata
      if (Latency == 0) begin : gen_comb
        assign rdata_o[g] = (req_i[g] && !we_i[g]) ? mem[addr_i[g]] : mem[r_addr_q[g]];
      end else begin : gen_pipe
        assign rdata_o[g] = rpipe_q[g][0];
      end
    end
  endgenerate

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (p = 0; p < NumPorts; p++) begin
        r_addr_q[p] <= '0;
        for (l = 0; l < EffLatency; l++) begin
          rpipe_q[p][l] <= '0;
        end
      end
    end else begin
      for (p = 0; p < NumPorts; p++) begin
        if (req_i[p]) begin
          r_addr_q[p] <= addr_i[p];
        end

        if (Latency != 0) begin
          for (l = 0; l < EffLatency-1; l++) begin
            rpipe_q[p][l] <= rpipe_q[p][l+1];
          end
          rpipe_q[p][EffLatency-1] <= (req_i[p] && !we_i[p]) ? mem[addr_i[p]] : mem[r_addr_q[p]];
        end
      end

      for (p = 0; p < NumPorts; p++) begin
        if (req_i[p] && we_i[p]) begin
          for (i = 0; i < BeWidth; i++) begin
            if (be_i[p][i]) begin
              mem[addr_i[p]][i*ByteWidth +: ByteWidth] <= wdata_i[p][i*ByteWidth +: ByteWidth];
            end
          end
        end
      end
    end
  end
endmodule
