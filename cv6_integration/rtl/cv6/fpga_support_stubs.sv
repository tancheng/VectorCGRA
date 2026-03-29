module SyncDpRam #(
  parameter ADDR_WIDTH = 10,
  parameter DATA_DEPTH = 1024,
  parameter DATA_WIDTH = 32,
  parameter OUT_REGS   = 0,
  parameter SIM_INIT   = 0
)(
  input  logic                  Clk_CI,
  input  logic                  Rst_RBI,
  input  logic                  CSelA_SI,
  input  logic                  WrEnA_SI,
  input  logic [DATA_WIDTH-1:0] WrDataA_DI,
  input  logic [ADDR_WIDTH-1:0] AddrA_DI,
  output logic [DATA_WIDTH-1:0] RdDataA_DO,
  input  logic                  CSelB_SI,
  input  logic                  WrEnB_SI,
  input  logic [DATA_WIDTH-1:0] WrDataB_DI,
  input  logic [ADDR_WIDTH-1:0] AddrB_DI,
  output logic [DATA_WIDTH-1:0] RdDataB_DO
);
  logic [DATA_WIDTH-1:0] mem [0:DATA_DEPTH-1];

  always_ff @(posedge Clk_CI or negedge Rst_RBI) begin
    if (!Rst_RBI) begin
      RdDataA_DO <= '0;
      RdDataB_DO <= '0;
    end else begin
      if (CSelA_SI) begin
        if (WrEnA_SI) mem[AddrA_DI] <= WrDataA_DI;
        RdDataA_DO <= mem[AddrA_DI];
      end
      if (CSelB_SI) begin
        if (WrEnB_SI) mem[AddrB_DI] <= WrDataB_DI;
        RdDataB_DO <= mem[AddrB_DI];
      end
    end
  end
endmodule

module AsyncDpRam #(
  parameter ADDR_WIDTH = 10,
  parameter DATA_DEPTH = 1024,
  parameter DATA_WIDTH = 32
)(
  input  logic                  Clk_CI,
  input  logic                  WrEn_SI,
  input  logic [ADDR_WIDTH-1:0] WrAddr_DI,
  input  logic [DATA_WIDTH-1:0] WrData_DI,
  input  logic [ADDR_WIDTH-1:0] RdAddr_DI,
  output logic [DATA_WIDTH-1:0] RdData_DO
);
  logic [DATA_WIDTH-1:0] mem [0:DATA_DEPTH-1];

  always_ff @(posedge Clk_CI) begin
    if (WrEn_SI) begin
      mem[WrAddr_DI] <= WrData_DI;
    end
  end

  assign RdData_DO = mem[RdAddr_DI];
endmodule

module AsyncThreePortRam #(
  parameter ADDR_WIDTH = 10,
  parameter DATA_DEPTH = 1024,
  parameter DATA_WIDTH = 32
)(
  input  logic                  Clk_CI,
  input  logic                  WrEn_SI,
  input  logic [ADDR_WIDTH-1:0] WrAddr_DI,
  input  logic [DATA_WIDTH-1:0] WrData_DI,
  input  logic [ADDR_WIDTH-1:0] RdAddr_DI_0,
  input  logic [ADDR_WIDTH-1:0] RdAddr_DI_1,
  output logic [DATA_WIDTH-1:0] RdData_DO_0,
  output logic [DATA_WIDTH-1:0] RdData_DO_1
);
  logic [DATA_WIDTH-1:0] mem [0:DATA_DEPTH-1];

  always_ff @(posedge Clk_CI) begin
    if (WrEn_SI) begin
      mem[WrAddr_DI] <= WrData_DI;
    end
  end

  assign RdData_DO_0 = mem[RdAddr_DI_0];
  assign RdData_DO_1 = mem[RdAddr_DI_1];
endmodule
