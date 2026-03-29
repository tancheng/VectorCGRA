module cv6_step_replay_tb;

  logic clk;
  logic rst_n;
  logic done;

  string script_hex;

  initial begin
    clk = 1'b0;
    forever #2 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (5) @(posedge clk);
    rst_n = 1'b1;
  end

  initial begin
    if (!$value$plusargs("SCRIPT=%s", script_hex)) begin
      script_hex = "generated/gemm_replay.hex";
    end
  end

  cv6_step_replay_top #(
    .SCRIPT_HEX(script_hex)
  ) dut (
    .clk_i(clk),
    .rst_ni(rst_n),
    .done_o(done)
  );

  initial begin
    repeat (200000) @(posedge clk);
    $fatal(1, "cv6_step_replay_tb timed out");
  end

  always @(posedge clk) begin
    if (done) begin
      $display("[cv6_step_replay_tb] completed");
      #10;
      $finish;
    end
  end

endmodule
