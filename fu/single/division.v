module division #(
    parameter WIDTH = 32,
    parameter ITER_BEGIN = 0,
    parameter ITER_END = 32
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

    reg [WIDTH:0]   r;      // 33-bit remainder (extra bit for overflow)
    reg [WIDTH-1:0] q;    // Quotient

    always @(*) begin
        integer i;

        r = r_i;
        q = q_i;

        for (i = ITER_BEGIN; i < ITER_END; i = i + 1) begin
            // Shift remainder left and insert next bit of dividend
            r = (r << 1) | ((dividend >> (31 - i)) & 1'b1);
            
            // Compare and subtract if possible
            if (r >= divisor) begin
                r = r - divisor;
                q[31 - i] = 1'b1;  // Set current quotient bit
            end else begin
                q[31 - i] = 1'b0;
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

    reg [WIDTH-1:0] qq[0:CYCLE-1];
    reg [WIDTH:0]   rr[0:CYCLE-1];
    wire [WIDTH-1:0] q[0:CYCLE-1];
    wire [WIDTH:0]   r[0:CYCLE-1];

    genvar i; 
    generate
        for (i = 0; i < CYCLE; i++) begin
            always @(posedge clk or posedge reset) begin
                if (reset) begin
                    qq[i] = 0;
                    rr[i] = 0;
                end
                else if (i < CYCLE - 1) begin
                    qq[i+1] = q[i];
                    rr[i+1] = r[i];
                end
                else begin
                    qq[i] = 0;
                    rr[i] = 0;
                end
            end
        end
    endgenerate

    generate
        for (i = 0; i < CYCLE; i++) begin
            division #(
                .WIDTH(WIDTH),
                .ITER_BEGIN(i*num_div),
                .ITER_END((i+1)*num_div)
            ) u0 (
                .clk(clk),
                .reset(reset),
                .dividend(dividend),
                .divisor(divisor),
                .q_i(qq[i]),
                .r_i(rr[i]),
                .q_o(q[i]),
                .r_o(r[i])
            );
        end
    endgenerate

    assign quotient  = q[CYCLE-1];
    assign remainder = r[CYCLE-1][WIDTH-1:0];

endmodule