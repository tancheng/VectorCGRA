/*
==========================================================================
division.v
==========================================================================
Integer division module for VectorCGRA.

Author : Jiajun Qin
  Date : 9 July, 2025
*/

module division #(
    parameter WIDTH      = 32,
    parameter ITER_BEGIN = 0,
    parameter ITER_END   = 32
) (
    input  clk,
    input  reset,
    input  [WIDTH-1:0] dividend,
    input  [WIDTH-1:0] divisor,
    input  [WIDTH:0]   r_i,
    input  [WIDTH-1:0] q_i,
    output  [WIDTH:0]   r_o,
    output  [WIDTH-1:0] q_o
);

    reg [WIDTH:0]   r;    // 33-bit remainder (extra bit for overflow)
    reg [WIDTH-1:0] q;    // Quotient

    parameter HIGHEST_BIT = WIDTH - 1;

    always @(*) begin
        integer i;

        r = r_i;
        q = q_i;

        for (i = ITER_BEGIN; i < ITER_END; i = i + 1) begin
            // Shift remainder left and insert next bit of dividend
            r = (r << 1) | ((dividend >> (HIGHEST_BIT - i)) & 1'b1);
            
            // Compare and subtract if possible
            if (r >= divisor) begin
                r = r - divisor;
                q[HIGHEST_BIT - i] = 1'b1;  // Set cur_ient quotient bit
            end else begin
                q[HIGHEST_BIT - i] = 1'b0;
            end
        end
    end

    assign r_o = r;
    assign q_o = q;

endmodule

module pipeline_division #(
    parameter WIDTH = 32,
    parameter CYCLE = 8
) (
    input  clk,
    input  reset,
    input  [WIDTH-1:0] dividend,
    input  [WIDTH-1:0] divisor,
    output [WIDTH-1:0] quotient,
    output [WIDTH-1:0] remainder
);

    parameter num_div = WIDTH / CYCLE;
    parameter res_div = WIDTH - CYCLE * num_div;

    // Pipeline registers between stages
    reg [WIDTH-1:0] q_i[0:CYCLE-1];             // Temporal quotient          
    reg [WIDTH:0]   r_i[0:CYCLE-1];             // Temporal remainder
    wire [WIDTH-1:0] q_o[0:CYCLE-1];
    wire [WIDTH:0]   r_o[0:CYCLE-1];

    // Pipeline registers for dividend and divisor
    // Since there could be CYCLE divisions in parallel,
    // we need to store the dividend and divisor for each stage.
    reg [WIDTH-1:0] dividend_reg[0:CYCLE-1];    
    reg [WIDTH-1:0] divisor_reg [0:CYCLE-1];

    genvar i; 

    assign dividend_reg[0] = dividend;
    assign divisor_reg[0]  = divisor;
    assign q_i[0] = 0;
    assign r_i[0] = 0;

    generate
        for (i = 0; i < CYCLE; i++) begin
            always @(posedge clk or posedge reset) begin
                if (reset) begin
                    q_i[i] <= 0;
                    r_i[i] <= 0;
                    dividend_reg[i] <= 0;
                    divisor_reg[i]  <= 0;
                end
                else if (i > 0) begin             // Propagate values through pipeline
                    q_i[i] <= q_i[i-1];           // Temporal quotient to next stage
                    r_i[i] <= r_i[i-1];           // Temporal remainder to next stage
                    dividend_reg[i] <= dividend_reg[i-1];       // Forward dividend
                    divisor_reg[i]  <= divisor_reg[i-1];        // Forward divisor
                end
            end
        end
    endgenerate

    generate
        for (i = 0; i < CYCLE; i++) begin
            division #(
                .WIDTH(WIDTH),
                .ITER_BEGIN(i * num_div),
                .ITER_END((i + 1) * num_div)
            ) u0 (
                .clk(clk),
                .reset(reset),
                .dividend(dividend_reg[i]),
                .divisor(divisor_reg[i]),
                .q_i(q_i[i]),
                .r_i(r_i[i]),
                .q_o(q_o[i]),
                .r_o(r_o[i])
            );
        end
    endgenerate

    // Final outputs from last pipeline stage
    assign quotient  = q_o[CYCLE-1];
    assign remainder = r_o[CYCLE-1][WIDTH-1:0];

endmodule