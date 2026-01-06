
// VT_INPUT_DELAY, VTB_OUTPUT_ASSERT_DELAY are timestamps relative to the rising edge.
`define VTB_INPUT_DELAY 1
`define VTB_OUTPUT_ASSERT_DELAY 3

// CYCLE_TIME and INTRA_CYCLE_TIME are duration of time.
`define CYCLE_TIME 4
`define INTRA_CYCLE_TIME (`VTB_OUTPUT_ASSERT_DELAY-`VTB_INPUT_DELAY)

`timescale 1ns/1ns

`define T(a0,a1,a2,a3,a4,a5) \
        t(a0,a1,a2,a3,a4,a5,`__LINE__)

// Tick one extra cycle upon an error.
`define VTB_TEST_FAIL(lineno, out, ref, port_name) \
    $display("- Timestamp      : %0d (default unit: ns)", $time); \
    $display("- Cycle number   : %0d (variable: cycle_count)", cycle_count); \
    $display("- line number    : line %0d in MeshMultiCgraRTL__975ce70dc1a0740a_test_multi_CGRA_fir_vector_global_reduce_tb.v.cases", lineno); \
    $display("- port name      : %s", port_name); \
    $display("- expected value : 0x%x", ref); \
    $display("- actual value   : 0x%x", out); \
    $display(""); \
    #(`CYCLE_TIME-`INTRA_CYCLE_TIME); \
    cycle_count += 1; \
    #`CYCLE_TIME; \
    cycle_count += 1; \
    $fatal;

`define CHECK(lineno, out, ref, port_name) \
  if ((|(out ^ out)) == 1'b0) ; \
  else begin \
    $display(""); \
    $display("The test bench received a value containing X/Z's! Please note"); \
    $display("that the VTB is pessmistic about X's and you should make sure"); \
    $display("all output ports of your DUT does not produce X's after reset."); \
    `VTB_TEST_FAIL(lineno, out, ref, port_name) \
  end \
  if (out != ref) begin \
    $display(""); \
    $display("The test bench received an incorrect value!"); \
    `VTB_TEST_FAIL(lineno, out, ref, port_name) \
  end

module MeshMultiCgraRTL__975ce70dc1a0740a_tb;
  // convention
  logic clk;
  logic reset;
  integer cycle_count;

  logic [216:0] recv_from_cpu_pkt__msg ;
  logic [0:0] recv_from_cpu_pkt__rdy ;
  logic [0:0] recv_from_cpu_pkt__val ;
  logic [216:0] send_to_cpu_pkt__msg ;
  logic [0:0] send_to_cpu_pkt__rdy ;
  logic [0:0] send_to_cpu_pkt__val ;

  task t(
    input logic [216:0] inp_recv_from_cpu_pkt__msg,
    input logic [0:0] ref_recv_from_cpu_pkt__rdy,
    input logic [0:0] inp_recv_from_cpu_pkt__val,
    input logic [216:0] ref_send_to_cpu_pkt__msg,
    input logic [0:0] inp_send_to_cpu_pkt__rdy,
    input logic [0:0] ref_send_to_cpu_pkt__val,
    integer lineno
  );
  begin
    recv_from_cpu_pkt__msg = inp_recv_from_cpu_pkt__msg;
    recv_from_cpu_pkt__val = inp_recv_from_cpu_pkt__val;
    send_to_cpu_pkt__rdy = inp_send_to_cpu_pkt__rdy;
    #`INTRA_CYCLE_TIME;
    `CHECK(lineno, recv_from_cpu_pkt__rdy, ref_recv_from_cpu_pkt__rdy, "recv_from_cpu_pkt.rdy (recv_from_cpu_pkt__rdy in Verilog)");
    `CHECK(lineno, send_to_cpu_pkt__msg, ref_send_to_cpu_pkt__msg, "send_to_cpu_pkt.msg (send_to_cpu_pkt__msg in Verilog)");
    `CHECK(lineno, send_to_cpu_pkt__val, ref_send_to_cpu_pkt__val, "send_to_cpu_pkt.val (send_to_cpu_pkt__val in Verilog)");
    #(`CYCLE_TIME-`INTRA_CYCLE_TIME);
    cycle_count += 1;
  end
  endtask

  // use 25% clock cycle, so #1 for setup #2 for sim #1 for hold
  always #(`CYCLE_TIME/2) clk = ~clk;

  // DUT name
  // By default we use the translated name of the Verilog component. But you can change
  // that by defining the VTB_TOP_MODULE_NAME macro through the simulator command line
  // options (e.g., for VCS you can do +define+VTB_TOP_MODULE_NAME=YourTopModuleName).
`ifdef VTB_TOP_MODULE_NAME
  `VTB_TOP_MODULE_NAME DUT
`else
  MeshMultiCgraRTL__975ce70dc1a0740a DUT
`endif
  (
    .clk(clk),
    .reset(reset),
    .recv_from_cpu_pkt__msg(recv_from_cpu_pkt__msg),
    .recv_from_cpu_pkt__rdy(recv_from_cpu_pkt__rdy),
    .recv_from_cpu_pkt__val(recv_from_cpu_pkt__val),
    .send_to_cpu_pkt__msg(send_to_cpu_pkt__msg),
    .send_to_cpu_pkt__rdy(send_to_cpu_pkt__rdy),
    .send_to_cpu_pkt__val(send_to_cpu_pkt__val)
  );

  initial begin
    assert(0 <= `VTB_INPUT_DELAY)
      else $fatal("\n=====\n\nVTB_INPUT_DELAY should >= 0\n\n=====\n");

    assert(`VTB_INPUT_DELAY < `VTB_OUTPUT_ASSERT_DELAY)
      else $fatal("\n=====\n\nVTB_OUTPUT_ASSERT_DELAY should be larger than VTB_INPUT_DELAY\n\n=====\n");

    assert(`VTB_OUTPUT_ASSERT_DELAY <= `CYCLE_TIME)
      else $fatal("\n=====\n\nVTB_OUTPUT_ASSERT_DELAY should be smaller than or equal to CYCLE_TIME\n\n=====\n");

    cycle_count = 0;
    clk   = 1'b0; // NEED TO DO THIS TO HAVE FALLING EDGE AT TIME 0
    reset = 1'b1; // TODO reset active low/high
    #(`CYCLE_TIME/2);

    // Now we are talking
    #`VTB_INPUT_DELAY;
    #`CYCLE_TIME;
    cycle_count = 1;
    #`CYCLE_TIME;
    cycle_count = 2;
    // 2 cycles plus input delay
    reset = 1'b0;

    `include "MeshMultiCgraRTL__975ce70dc1a0740a_test_multi_CGRA_fir_vector_global_reduce_tb.v.cases"

    $display("");
    $display("  [ passed ]");
    $display("");

    // Tick one extra cycle for better waveform
    #`CYCLE_TIME;
    cycle_count += 1;
    $finish;
  end
endmodule
