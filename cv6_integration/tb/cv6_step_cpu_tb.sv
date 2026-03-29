module cv6_step_cpu_tb;
  logic clk;
  logic rst_n;
  logic [31:0] exit_code;

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (20) @(posedge clk);
    rst_n = 1'b1;
  end

  cv6_step_testharness #(
    .DRAM_INIT_FILE("generated/step_gemm.memh")
  ) dut (
    .clk_i(clk),
    .rst_ni(rst_n),
    .exit_o(exit_code)
  );

  initial begin
    repeat (1000000) @(posedge clk);
    $fatal(1, "cv6_step_cpu_tb timed out");
  end

  always @(posedge clk) begin
    if (exit_code != 32'd0) begin
      $display("[cv6_step_cpu_tb] exit=%0d", exit_code);
      #20;
      $finish;
    end
  end
endmodule
