module Mux__9f2a715e2ee264ce (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [417:0] in_;
	output reg [208:0] out;
	input wire [0:0] reset;
	input wire [0:0] sel;
	always @(*) begin : up_mux
		out = in_[(1 - sel) * 209+:209];
	end
endmodule
module BypassQueue1EntryRTL__b3a1aa7cee3cfb56 (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [0:0] count;
	input wire [0:0] reset;
	input wire [208:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [208:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	reg [208:0] entry;
	reg [0:0] full;
	wire [0:0] bypass_mux__clk;
	wire [417:0] bypass_mux__in_;
	wire [208:0] bypass_mux__out;
	wire [0:0] bypass_mux__reset;
	wire [0:0] bypass_mux__sel;
	Mux__9f2a715e2ee264ce bypass_mux(
		.clk(bypass_mux__clk),
		.in_(bypass_mux__in_),
		.out(bypass_mux__out),
		.reset(bypass_mux__reset),
		.sel(bypass_mux__sel)
	);
	always @(*) begin : _lambda__s_dut_bypass_queue_q_recv_rdy
		recv__rdy = ~full;
	end
	always @(*) begin : _lambda__s_dut_bypass_queue_q_send_val
		send__val = full | recv__val;
	end
	always @(posedge clk) begin : ff_bypass1
		if (reset)
			full <= 1'd0;
		else
			full <= ~send__rdy & (full | recv__val);
		if ((~send__rdy & ~full) & recv__val)
			entry <= recv__msg;
	end
	assign bypass_mux__clk = clk;
	assign bypass_mux__reset = reset;
	assign bypass_mux__in_[209+:209] = recv__msg;
	assign bypass_mux__in_[0+:209] = entry;
	assign send__msg = bypass_mux__out;
	assign bypass_mux__sel = full;
	assign count = full;
endmodule
module BypassQueueRTL__16564dc625bb50ae (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [0:0] count;
	input wire [0:0] reset;
	input wire [208:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [208:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] q__clk;
	wire [0:0] q__count;
	wire [0:0] q__reset;
	wire [208:0] q__recv__msg;
	wire [0:0] q__recv__rdy;
	wire [0:0] q__recv__val;
	wire [208:0] q__send__msg;
	wire [0:0] q__send__rdy;
	wire [0:0] q__send__val;
	BypassQueue1EntryRTL__b3a1aa7cee3cfb56 q(
		.clk(q__clk),
		.count(q__count),
		.reset(q__reset),
		.recv__msg(q__recv__msg),
		.recv__rdy(q__recv__rdy),
		.recv__val(q__recv__val),
		.send__msg(q__send__msg),
		.send__rdy(q__send__rdy),
		.send__val(q__send__val)
	);
	assign q__clk = clk;
	assign q__reset = reset;
	assign q__recv__msg = recv__msg;
	assign recv__rdy = q__recv__rdy;
	assign q__recv__val = recv__val;
	assign send__msg = q__send__msg;
	assign q__send__rdy = send__rdy;
	assign send__val = q__send__val;
	assign count = q__count;
endmodule
module BypassQueueCtrlRTL__num_entries_2 (
	clk,
	count,
	mux_sel,
	raddr,
	recv_rdy,
	recv_val,
	reset,
	send_rdy,
	send_val,
	waddr,
	wen
);
	input wire [0:0] clk;
	output reg [1:0] count;
	output reg [0:0] mux_sel;
	output wire [0:0] raddr;
	output reg [0:0] recv_rdy;
	input wire [0:0] recv_val;
	input wire [0:0] reset;
	input wire [0:0] send_rdy;
	output reg [0:0] send_val;
	output wire [0:0] waddr;
	output wire [0:0] wen;
	localparam [1:0] __const__num_entries_at__lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_recv_rdy = 2'd2;
	localparam [1:0] __const__num_entries_at_up_reg = 2'd2;
	reg [0:0] head;
	reg [0:0] recv_xfer;
	reg [0:0] send_xfer;
	reg [0:0] tail;
	always @(*) begin : _lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_mux_sel
		mux_sel = count == 2'd0;
	end
	always @(*) begin : _lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_recv_rdy
		recv_rdy = count < __const__num_entries_at__lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_recv_rdy;
	end
	always @(*) begin : _lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_recv_xfer
		recv_xfer = recv_val & recv_rdy;
	end
	always @(*) begin : _lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_send_val
		send_val = (count > 2'd0) | recv_val;
	end
	always @(*) begin : _lambda__s_dut_controller_crossbar_input_units_0__queue_ctrl_send_xfer
		send_xfer = send_val & send_rdy;
	end
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(posedge clk) begin : up_reg
		if (reset) begin
			head <= 1'd0;
			tail <= 1'd0;
			count <= 2'd0;
		end
		else begin
			if (recv_xfer)
				tail <= (tail < (sv2v_cast_1(__const__num_entries_at_up_reg) - 1'd1) ? tail + 1'd1 : 1'd0);
			if (send_xfer)
				head <= (head < (sv2v_cast_1(__const__num_entries_at_up_reg) - 1'd1) ? head + 1'd1 : 1'd0);
			if (recv_xfer & ~send_xfer)
				count <= count + 2'd1;
			if (~recv_xfer & send_xfer)
				count <= count - 2'd1;
		end
	end
	assign wen = recv_xfer;
	assign waddr = tail;
	assign raddr = head;
endmodule
module Mux__698f7a7bf81407b2 (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [419:0] in_;
	output reg [209:0] out;
	input wire [0:0] reset;
	input wire [0:0] sel;
	always @(*) begin : up_mux
		out = in_[(1 - sel) * 210+:210];
	end
endmodule
module RegisterFile__30a5b21da63837e8 (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	output reg [209:0] rdata;
	input wire [0:0] reset;
	input wire [0:0] waddr;
	input wire [209:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [209:0] regs [0:1];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 210+:210] = regs[raddr[sv2v_cast_1(i)+:1]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i)+:1]] <= wdata[sv2v_cast_1(i) * 210+:210];
		end
	end
endmodule
module BypassQueueDpathRTL__ee868ebbad6732e2 (
	clk,
	mux_sel,
	raddr,
	recv_msg,
	reset,
	send_msg,
	waddr,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] mux_sel;
	input wire [0:0] raddr;
	input wire [209:0] recv_msg;
	input wire [0:0] reset;
	output wire [209:0] send_msg;
	input wire [0:0] waddr;
	input wire [0:0] wen;
	wire [0:0] mux__clk;
	wire [419:0] mux__in_;
	wire [209:0] mux__out;
	wire [0:0] mux__reset;
	wire [0:0] mux__sel;
	Mux__698f7a7bf81407b2 mux(
		.clk(mux__clk),
		.in_(mux__in_),
		.out(mux__out),
		.reset(mux__reset),
		.sel(mux__sel)
	);
	wire [0:0] rf__clk;
	wire [0:0] rf__raddr;
	wire [209:0] rf__rdata;
	wire [0:0] rf__reset;
	wire [0:0] rf__waddr;
	wire [209:0] rf__wdata;
	wire [0:0] rf__wen;
	RegisterFile__30a5b21da63837e8 rf(
		.clk(rf__clk),
		.raddr(rf__raddr),
		.rdata(rf__rdata),
		.reset(rf__reset),
		.waddr(rf__waddr),
		.wdata(rf__wdata),
		.wen(rf__wen)
	);
	assign rf__clk = clk;
	assign rf__reset = reset;
	assign rf__raddr[0+:1] = raddr;
	assign rf__wen[0+:1] = wen;
	assign rf__waddr[0+:1] = waddr;
	assign rf__wdata[0+:210] = recv_msg;
	assign mux__clk = clk;
	assign mux__reset = reset;
	assign mux__sel = mux_sel;
	assign mux__in_[210+:210] = rf__rdata[0+:210];
	assign mux__in_[0+:210] = recv_msg;
	assign send_msg = mux__out;
endmodule
module BypassQueueRTL__ee868ebbad6732e2 (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1:0] count;
	input wire [0:0] reset;
	input wire [209:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [209:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] ctrl__clk;
	wire [1:0] ctrl__count;
	wire [0:0] ctrl__mux_sel;
	wire [0:0] ctrl__raddr;
	wire [0:0] ctrl__recv_rdy;
	wire [0:0] ctrl__recv_val;
	wire [0:0] ctrl__reset;
	wire [0:0] ctrl__send_rdy;
	wire [0:0] ctrl__send_val;
	wire [0:0] ctrl__waddr;
	wire [0:0] ctrl__wen;
	BypassQueueCtrlRTL__num_entries_2 ctrl(
		.clk(ctrl__clk),
		.count(ctrl__count),
		.mux_sel(ctrl__mux_sel),
		.raddr(ctrl__raddr),
		.recv_rdy(ctrl__recv_rdy),
		.recv_val(ctrl__recv_val),
		.reset(ctrl__reset),
		.send_rdy(ctrl__send_rdy),
		.send_val(ctrl__send_val),
		.waddr(ctrl__waddr),
		.wen(ctrl__wen)
	);
	wire [0:0] dpath__clk;
	wire [0:0] dpath__mux_sel;
	wire [0:0] dpath__raddr;
	wire [209:0] dpath__recv_msg;
	wire [0:0] dpath__reset;
	wire [209:0] dpath__send_msg;
	wire [0:0] dpath__waddr;
	wire [0:0] dpath__wen;
	BypassQueueDpathRTL__ee868ebbad6732e2 dpath(
		.clk(dpath__clk),
		.mux_sel(dpath__mux_sel),
		.raddr(dpath__raddr),
		.recv_msg(dpath__recv_msg),
		.reset(dpath__reset),
		.send_msg(dpath__send_msg),
		.waddr(dpath__waddr),
		.wen(dpath__wen)
	);
	assign ctrl__clk = clk;
	assign ctrl__reset = reset;
	assign dpath__clk = clk;
	assign dpath__reset = reset;
	assign dpath__wen = ctrl__wen;
	assign dpath__waddr = ctrl__waddr;
	assign dpath__raddr = ctrl__raddr;
	assign dpath__mux_sel = ctrl__mux_sel;
	assign ctrl__recv_val = recv__val;
	assign recv__rdy = ctrl__recv_rdy;
	assign send__val = ctrl__send_val;
	assign ctrl__send_rdy = send__rdy;
	assign count = ctrl__count;
	assign dpath__recv_msg = recv__msg;
	assign send__msg = dpath__send_msg;
endmodule
module InputUnitRTL__1211c5d9deccc2e1 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [209:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [209:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] queue__clk;
	wire [1:0] queue__count;
	wire [0:0] queue__reset;
	wire [209:0] queue__recv__msg;
	wire [0:0] queue__recv__rdy;
	wire [0:0] queue__recv__val;
	wire [209:0] queue__send__msg;
	wire [0:0] queue__send__rdy;
	wire [0:0] queue__send__val;
	BypassQueueRTL__ee868ebbad6732e2 queue(
		.clk(queue__clk),
		.count(queue__count),
		.reset(queue__reset),
		.recv__msg(queue__recv__msg),
		.recv__rdy(queue__recv__rdy),
		.recv__val(queue__recv__val),
		.send__msg(queue__send__msg),
		.send__rdy(queue__send__rdy),
		.send__val(queue__send__val)
	);
	assign queue__clk = clk;
	assign queue__reset = reset;
	assign queue__recv__msg = recv__msg;
	assign recv__rdy = queue__recv__rdy;
	assign queue__recv__val = recv__val;
	assign send__msg = queue__send__msg;
	assign queue__send__rdy = send__rdy;
	assign send__val = queue__send__val;
endmodule
module OutputUnitRTL__3506d42bf691469a (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [209:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [209:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	assign send__msg = recv__msg;
	assign recv__rdy = send__rdy;
	assign send__val = recv__val;
endmodule
module XbarRouteUnitRTL__1cc47a07bcb2fcc0 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [209:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [209:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	localparam [0:0] __const__num_outports_at_up_ru_routing = 1'd1;
	reg [0:0] out_dir;
	wire [0:0] send_val;
	always @(*) begin : up_ru_recv_rdy
		recv__rdy = send__rdy[out_dir+:1] > 1'd0;
	end
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_ru_routing
		out_dir = recv__msg[209];
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_up_ru_routing; i = i + 1'd1)
				send__val[sv2v_cast_1(i)+:1] = 1'd0;
		end
		if (recv__val)
			send__val[out_dir+:1] = 1'd1;
	end
	assign send__msg[0+:210] = recv__msg;
	assign send_val[0:0] = send__val[0+:1];
endmodule
module RegEnRst__Type_Bits5__reset_value_1 (
	clk,
	en,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	input wire [4:0] in_;
	output reg [4:0] out;
	input wire [0:0] reset;
	localparam [0:0] __const__reset_value_at_up_regenrst = 1'd1;
	function automatic [4:0] sv2v_cast_5;
		input reg [4:0] inp;
		sv2v_cast_5 = inp;
	endfunction
	always @(posedge clk) begin : up_regenrst
		if (reset)
			out <= sv2v_cast_5(__const__reset_value_at_up_regenrst);
		else if (en)
			out <= in_;
	end
endmodule
module RoundRobinArbiterEn__nreqs_5 (
	clk,
	en,
	grants,
	reqs,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	output reg [4:0] grants;
	input wire [4:0] reqs;
	input wire [0:0] reset;
	localparam [2:0] __const__nreqs_at_comb_reqs_int = 3'd5;
	localparam [3:0] __const__nreqsX2_at_comb_reqs_int = 4'd10;
	localparam [2:0] __const__nreqs_at_comb_grants = 3'd5;
	localparam [2:0] __const__nreqs_at_comb_priority_int = 3'd5;
	localparam [3:0] __const__nreqsX2_at_comb_priority_int = 4'd10;
	localparam [3:0] __const__nreqsX2_at_comb_kills = 4'd10;
	localparam [3:0] __const__nreqsX2_at_comb_grants_int = 4'd10;
	reg [9:0] grants_int;
	reg [10:0] kills;
	reg [0:0] priority_en;
	reg [9:0] priority_int;
	reg [9:0] reqs_int;
	wire [0:0] priority_reg__clk;
	wire [0:0] priority_reg__en;
	wire [4:0] priority_reg__in_;
	wire [4:0] priority_reg__out;
	wire [0:0] priority_reg__reset;
	RegEnRst__Type_Bits5__reset_value_1 priority_reg(
		.clk(priority_reg__clk),
		.en(priority_reg__en),
		.in_(priority_reg__in_),
		.out(priority_reg__out),
		.reset(priority_reg__reset)
	);
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	always @(*) begin : comb_grants
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqs_at_comb_grants; i = i + 1'd1)
				grants[sv2v_cast_3(i)] = grants_int[sv2v_cast_4(i)] | grants_int[sv2v_cast_4(__const__nreqs_at_comb_grants) + sv2v_cast_4(i)];
		end
	end
	always @(*) begin : comb_grants_int
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_grants_int; i = i + 1'd1)
				if (priority_int[sv2v_cast_4(i)])
					grants_int[sv2v_cast_4(i)] = reqs_int[sv2v_cast_4(i)];
				else
					grants_int[sv2v_cast_4(i)] = ~kills[sv2v_cast_4(i)] & reqs_int[sv2v_cast_4(i)];
		end
	end
	always @(*) begin : comb_kills
		kills[4'd0] = 1'd1;
		begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_kills; i = i + 1'd1)
				if (priority_int[sv2v_cast_4(i)])
					kills[sv2v_cast_4(i) + 4'd1] = reqs_int[sv2v_cast_4(i)];
				else
					kills[sv2v_cast_4(i) + 4'd1] = kills[sv2v_cast_4(i)] | (~kills[sv2v_cast_4(i)] & reqs_int[sv2v_cast_4(i)]);
		end
	end
	always @(*) begin : comb_priority_en
		priority_en = (grants != 5'd0) & en;
	end
	always @(*) begin : comb_priority_int
		priority_int[4'd4:4'd0] = priority_reg__out;
		priority_int[4'd9:sv2v_cast_4(__const__nreqs_at_comb_priority_int)] = 5'd0;
	end
	always @(*) begin : comb_reqs_int
		reqs_int[4'd4:4'd0] = reqs;
		reqs_int[4'd9:sv2v_cast_4(__const__nreqs_at_comb_reqs_int)] = reqs;
	end
	assign priority_reg__clk = clk;
	assign priority_reg__reset = reset;
	assign priority_reg__en = priority_en;
	assign priority_reg__in_[4:1] = grants[3:0];
	assign priority_reg__in_[0:0] = grants[4:4];
endmodule
module Encoder__in_nbits_5__out_nbits_3 (
	clk,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [4:0] in_;
	output reg [2:0] out;
	input wire [0:0] reset;
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : encode
		out = 3'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < 3'd5; i = i + 1'd1)
				if (in_[sv2v_cast_3(i)])
					out = sv2v_cast_3(i);
		end
	end
endmodule
module Mux__667e445af340972d (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [1049:0] in_;
	output reg [209:0] out;
	input wire [0:0] reset;
	input wire [2:0] sel;
	always @(*) begin : up_mux
		out = in_[(4 - sel) * 210+:210];
	end
endmodule
module SwitchUnitRTL__da8e26e230838e15 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [1049:0] recv__msg;
	output reg [4:0] recv__rdy;
	input wire [4:0] recv__val;
	output wire [209:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	localparam [2:0] __const__num_inports_at_up_get_en = 3'd5;
	wire [0:0] arbiter__clk;
	wire [0:0] arbiter__en;
	wire [4:0] arbiter__grants;
	wire [4:0] arbiter__reqs;
	wire [0:0] arbiter__reset;
	RoundRobinArbiterEn__nreqs_5 arbiter(
		.clk(arbiter__clk),
		.en(arbiter__en),
		.grants(arbiter__grants),
		.reqs(arbiter__reqs),
		.reset(arbiter__reset)
	);
	wire [0:0] encoder__clk;
	wire [4:0] encoder__in_;
	wire [2:0] encoder__out;
	wire [0:0] encoder__reset;
	Encoder__in_nbits_5__out_nbits_3 encoder(
		.clk(encoder__clk),
		.in_(encoder__in_),
		.out(encoder__out),
		.reset(encoder__reset)
	);
	wire [0:0] mux__clk;
	wire [1049:0] mux__in_;
	wire [209:0] mux__out;
	wire [0:0] mux__reset;
	wire [2:0] mux__sel;
	Mux__667e445af340972d mux(
		.clk(mux__clk),
		.in_(mux__in_),
		.out(mux__out),
		.reset(mux__reset),
		.sel(mux__sel)
	);
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : up_get_en
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_up_get_en; i = i + 1'd1)
				recv__rdy[4 - sv2v_cast_3(i)+:1] = send__rdy & (mux__sel == sv2v_cast_3(i));
		end
	end
	always @(*) begin : up_send_val
		send__val = arbiter__grants > 5'd0;
	end
	assign arbiter__clk = clk;
	assign arbiter__reset = reset;
	assign arbiter__en = 1'd1;
	assign mux__clk = clk;
	assign mux__reset = reset;
	assign send__msg = mux__out;
	assign encoder__clk = clk;
	assign encoder__reset = reset;
	assign encoder__in_ = arbiter__grants;
	assign mux__sel = encoder__out;
	assign arbiter__reqs[0:0] = recv__val[4+:1];
	assign mux__in_[840+:210] = recv__msg[840+:210];
	assign arbiter__reqs[1:1] = recv__val[3+:1];
	assign mux__in_[630+:210] = recv__msg[630+:210];
	assign arbiter__reqs[2:2] = recv__val[2+:1];
	assign mux__in_[420+:210] = recv__msg[420+:210];
	assign arbiter__reqs[3:3] = recv__val[1+:1];
	assign mux__in_[210+:210] = recv__msg[210+:210];
	assign arbiter__reqs[4:4] = recv__val[0+:1];
	assign mux__in_[0+:210] = recv__msg[0+:210];
endmodule
module XbarBypassQueueRTL__cf118fbc1901d815 (
	clk,
	packet_on_input_units,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1049:0] packet_on_input_units;
	input wire [0:0] reset;
	input wire [1049:0] recv__msg;
	output wire [4:0] recv__rdy;
	input wire [4:0] recv__val;
	output wire [209:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] input_units__clk [0:4];
	wire [0:0] input_units__reset [0:4];
	wire [209:0] input_units__recv__msg [0:4];
	wire [0:0] input_units__recv__rdy [0:4];
	wire [0:0] input_units__recv__val [0:4];
	wire [209:0] input_units__send__msg [0:4];
	wire [0:0] input_units__send__rdy [0:4];
	wire [0:0] input_units__send__val [0:4];
	InputUnitRTL__1211c5d9deccc2e1 input_units__0(
		.clk(input_units__clk[0]),
		.reset(input_units__reset[0]),
		.recv__msg(input_units__recv__msg[0]),
		.recv__rdy(input_units__recv__rdy[0]),
		.recv__val(input_units__recv__val[0]),
		.send__msg(input_units__send__msg[0]),
		.send__rdy(input_units__send__rdy[0]),
		.send__val(input_units__send__val[0])
	);
	InputUnitRTL__1211c5d9deccc2e1 input_units__1(
		.clk(input_units__clk[1]),
		.reset(input_units__reset[1]),
		.recv__msg(input_units__recv__msg[1]),
		.recv__rdy(input_units__recv__rdy[1]),
		.recv__val(input_units__recv__val[1]),
		.send__msg(input_units__send__msg[1]),
		.send__rdy(input_units__send__rdy[1]),
		.send__val(input_units__send__val[1])
	);
	InputUnitRTL__1211c5d9deccc2e1 input_units__2(
		.clk(input_units__clk[2]),
		.reset(input_units__reset[2]),
		.recv__msg(input_units__recv__msg[2]),
		.recv__rdy(input_units__recv__rdy[2]),
		.recv__val(input_units__recv__val[2]),
		.send__msg(input_units__send__msg[2]),
		.send__rdy(input_units__send__rdy[2]),
		.send__val(input_units__send__val[2])
	);
	InputUnitRTL__1211c5d9deccc2e1 input_units__3(
		.clk(input_units__clk[3]),
		.reset(input_units__reset[3]),
		.recv__msg(input_units__recv__msg[3]),
		.recv__rdy(input_units__recv__rdy[3]),
		.recv__val(input_units__recv__val[3]),
		.send__msg(input_units__send__msg[3]),
		.send__rdy(input_units__send__rdy[3]),
		.send__val(input_units__send__val[3])
	);
	InputUnitRTL__1211c5d9deccc2e1 input_units__4(
		.clk(input_units__clk[4]),
		.reset(input_units__reset[4]),
		.recv__msg(input_units__recv__msg[4]),
		.recv__rdy(input_units__recv__rdy[4]),
		.recv__val(input_units__recv__val[4]),
		.send__msg(input_units__send__msg[4]),
		.send__rdy(input_units__send__rdy[4]),
		.send__val(input_units__send__val[4])
	);
	wire [0:0] output_units__clk [0:0];
	wire [0:0] output_units__reset [0:0];
	wire [209:0] output_units__recv__msg [0:0];
	wire [0:0] output_units__recv__rdy [0:0];
	wire [0:0] output_units__recv__val [0:0];
	wire [209:0] output_units__send__msg [0:0];
	wire [0:0] output_units__send__rdy [0:0];
	wire [0:0] output_units__send__val [0:0];
	OutputUnitRTL__3506d42bf691469a output_units__0(
		.clk(output_units__clk[0]),
		.reset(output_units__reset[0]),
		.recv__msg(output_units__recv__msg[0]),
		.recv__rdy(output_units__recv__rdy[0]),
		.recv__val(output_units__recv__val[0]),
		.send__msg(output_units__send__msg[0]),
		.send__rdy(output_units__send__rdy[0]),
		.send__val(output_units__send__val[0])
	);
	wire [0:0] route_units__clk [0:4];
	wire [0:0] route_units__reset [0:4];
	wire [209:0] route_units__recv__msg [0:4];
	wire [0:0] route_units__recv__rdy [0:4];
	wire [0:0] route_units__recv__val [0:4];
	wire [209:0] route_units__send__msg [0:4];
	wire [0:0] route_units__send__rdy [0:4];
	wire [0:0] route_units__send__val [0:4];
	XbarRouteUnitRTL__1cc47a07bcb2fcc0 route_units__0(
		.clk(route_units__clk[0]),
		.reset(route_units__reset[0]),
		.recv__msg(route_units__recv__msg[0]),
		.recv__rdy(route_units__recv__rdy[0]),
		.recv__val(route_units__recv__val[0]),
		.send__msg(route_units__send__msg[0]),
		.send__rdy(route_units__send__rdy[0]),
		.send__val(route_units__send__val[0])
	);
	XbarRouteUnitRTL__1cc47a07bcb2fcc0 route_units__1(
		.clk(route_units__clk[1]),
		.reset(route_units__reset[1]),
		.recv__msg(route_units__recv__msg[1]),
		.recv__rdy(route_units__recv__rdy[1]),
		.recv__val(route_units__recv__val[1]),
		.send__msg(route_units__send__msg[1]),
		.send__rdy(route_units__send__rdy[1]),
		.send__val(route_units__send__val[1])
	);
	XbarRouteUnitRTL__1cc47a07bcb2fcc0 route_units__2(
		.clk(route_units__clk[2]),
		.reset(route_units__reset[2]),
		.recv__msg(route_units__recv__msg[2]),
		.recv__rdy(route_units__recv__rdy[2]),
		.recv__val(route_units__recv__val[2]),
		.send__msg(route_units__send__msg[2]),
		.send__rdy(route_units__send__rdy[2]),
		.send__val(route_units__send__val[2])
	);
	XbarRouteUnitRTL__1cc47a07bcb2fcc0 route_units__3(
		.clk(route_units__clk[3]),
		.reset(route_units__reset[3]),
		.recv__msg(route_units__recv__msg[3]),
		.recv__rdy(route_units__recv__rdy[3]),
		.recv__val(route_units__recv__val[3]),
		.send__msg(route_units__send__msg[3]),
		.send__rdy(route_units__send__rdy[3]),
		.send__val(route_units__send__val[3])
	);
	XbarRouteUnitRTL__1cc47a07bcb2fcc0 route_units__4(
		.clk(route_units__clk[4]),
		.reset(route_units__reset[4]),
		.recv__msg(route_units__recv__msg[4]),
		.recv__rdy(route_units__recv__rdy[4]),
		.recv__val(route_units__recv__val[4]),
		.send__msg(route_units__send__msg[4]),
		.send__rdy(route_units__send__rdy[4]),
		.send__val(route_units__send__val[4])
	);
	wire [0:0] switch_units__clk [0:0];
	wire [0:0] switch_units__reset [0:0];
	wire [1049:0] switch_units__recv__msg [0:0];
	wire [4:0] switch_units__recv__rdy [0:0];
	wire [4:0] switch_units__recv__val [0:0];
	wire [209:0] switch_units__send__msg [0:0];
	wire [0:0] switch_units__send__rdy [0:0];
	wire [0:0] switch_units__send__val [0:0];
	SwitchUnitRTL__da8e26e230838e15 switch_units__0(
		.clk(switch_units__clk[0]),
		.reset(switch_units__reset[0]),
		.recv__msg(switch_units__recv__msg[0]),
		.recv__rdy(switch_units__recv__rdy[0]),
		.recv__val(switch_units__recv__val[0]),
		.send__msg(switch_units__send__msg[0]),
		.send__rdy(switch_units__send__rdy[0]),
		.send__val(switch_units__send__val[0])
	);
	assign input_units__clk[0] = clk;
	assign input_units__reset[0] = reset;
	assign input_units__clk[1] = clk;
	assign input_units__reset[1] = reset;
	assign input_units__clk[2] = clk;
	assign input_units__reset[2] = reset;
	assign input_units__clk[3] = clk;
	assign input_units__reset[3] = reset;
	assign input_units__clk[4] = clk;
	assign input_units__reset[4] = reset;
	assign route_units__clk[0] = clk;
	assign route_units__reset[0] = reset;
	assign route_units__clk[1] = clk;
	assign route_units__reset[1] = reset;
	assign route_units__clk[2] = clk;
	assign route_units__reset[2] = reset;
	assign route_units__clk[3] = clk;
	assign route_units__reset[3] = reset;
	assign route_units__clk[4] = clk;
	assign route_units__reset[4] = reset;
	assign switch_units__clk[0] = clk;
	assign switch_units__reset[0] = reset;
	assign output_units__clk[0] = clk;
	assign output_units__reset[0] = reset;
	assign packet_on_input_units[840+:210] = input_units__send__msg[0];
	assign packet_on_input_units[630+:210] = input_units__send__msg[1];
	assign packet_on_input_units[420+:210] = input_units__send__msg[2];
	assign packet_on_input_units[210+:210] = input_units__send__msg[3];
	assign packet_on_input_units[0+:210] = input_units__send__msg[4];
	assign input_units__recv__msg[0] = recv__msg[840+:210];
	assign recv__rdy[4+:1] = input_units__recv__rdy[0];
	assign input_units__recv__val[0] = recv__val[4+:1];
	assign route_units__recv__msg[0] = input_units__send__msg[0];
	assign input_units__send__rdy[0] = route_units__recv__rdy[0];
	assign route_units__recv__val[0] = input_units__send__val[0];
	assign input_units__recv__msg[1] = recv__msg[630+:210];
	assign recv__rdy[3+:1] = input_units__recv__rdy[1];
	assign input_units__recv__val[1] = recv__val[3+:1];
	assign route_units__recv__msg[1] = input_units__send__msg[1];
	assign input_units__send__rdy[1] = route_units__recv__rdy[1];
	assign route_units__recv__val[1] = input_units__send__val[1];
	assign input_units__recv__msg[2] = recv__msg[420+:210];
	assign recv__rdy[2+:1] = input_units__recv__rdy[2];
	assign input_units__recv__val[2] = recv__val[2+:1];
	assign route_units__recv__msg[2] = input_units__send__msg[2];
	assign input_units__send__rdy[2] = route_units__recv__rdy[2];
	assign route_units__recv__val[2] = input_units__send__val[2];
	assign input_units__recv__msg[3] = recv__msg[210+:210];
	assign recv__rdy[1+:1] = input_units__recv__rdy[3];
	assign input_units__recv__val[3] = recv__val[1+:1];
	assign route_units__recv__msg[3] = input_units__send__msg[3];
	assign input_units__send__rdy[3] = route_units__recv__rdy[3];
	assign route_units__recv__val[3] = input_units__send__val[3];
	assign input_units__recv__msg[4] = recv__msg[0+:210];
	assign recv__rdy[0+:1] = input_units__recv__rdy[4];
	assign input_units__recv__val[4] = recv__val[0+:1];
	assign route_units__recv__msg[4] = input_units__send__msg[4];
	assign input_units__send__rdy[4] = route_units__recv__rdy[4];
	assign route_units__recv__val[4] = input_units__send__val[4];
	assign switch_units__recv__msg[0][840+:210] = route_units__send__msg[0][0+:210];
	assign route_units__send__rdy[0][0+:1] = switch_units__recv__rdy[0][4+:1];
	assign switch_units__recv__val[0][4+:1] = route_units__send__val[0][0+:1];
	assign switch_units__recv__msg[0][630+:210] = route_units__send__msg[1][0+:210];
	assign route_units__send__rdy[1][0+:1] = switch_units__recv__rdy[0][3+:1];
	assign switch_units__recv__val[0][3+:1] = route_units__send__val[1][0+:1];
	assign switch_units__recv__msg[0][420+:210] = route_units__send__msg[2][0+:210];
	assign route_units__send__rdy[2][0+:1] = switch_units__recv__rdy[0][2+:1];
	assign switch_units__recv__val[0][2+:1] = route_units__send__val[2][0+:1];
	assign switch_units__recv__msg[0][210+:210] = route_units__send__msg[3][0+:210];
	assign route_units__send__rdy[3][0+:1] = switch_units__recv__rdy[0][1+:1];
	assign switch_units__recv__val[0][1+:1] = route_units__send__val[3][0+:1];
	assign switch_units__recv__msg[0][0+:210] = route_units__send__msg[4][0+:210];
	assign route_units__send__rdy[4][0+:1] = switch_units__recv__rdy[0][0+:1];
	assign switch_units__recv__val[0][0+:1] = route_units__send__val[4][0+:1];
	assign output_units__recv__msg[0] = switch_units__send__msg[0];
	assign switch_units__send__rdy[0] = output_units__recv__rdy[0];
	assign output_units__recv__val[0] = switch_units__send__val[0];
	assign send__msg[0+:210] = output_units__send__msg[0];
	assign output_units__send__rdy[0] = send__rdy[0+:1];
	assign send__val[0+:1] = output_units__send__val[0];
endmodule
module NormalQueueCtrlRTL__num_entries_2 (
	clk,
	count,
	raddr,
	recv_rdy,
	recv_val,
	reset,
	send_rdy,
	send_val,
	waddr,
	wen
);
	input wire [0:0] clk;
	output reg [1:0] count;
	output wire [0:0] raddr;
	output reg [0:0] recv_rdy;
	input wire [0:0] recv_val;
	input wire [0:0] reset;
	input wire [0:0] send_rdy;
	output reg [0:0] send_val;
	output wire [0:0] waddr;
	output wire [0:0] wen;
	localparam [1:0] __const__num_entries_at__lambda__s_dut_controller_recv_from_cpu_pkt_queue_ctrl_recv_rdy = 2'd2;
	localparam [1:0] __const__num_entries_at_up_reg = 2'd2;
	reg [0:0] head;
	reg [0:0] recv_xfer;
	reg [0:0] send_xfer;
	reg [0:0] tail;
	always @(*) begin : _lambda__s_dut_controller_recv_from_cpu_pkt_queue_ctrl_recv_rdy
		recv_rdy = count < __const__num_entries_at__lambda__s_dut_controller_recv_from_cpu_pkt_queue_ctrl_recv_rdy;
	end
	always @(*) begin : _lambda__s_dut_controller_recv_from_cpu_pkt_queue_ctrl_recv_xfer
		recv_xfer = recv_val & recv_rdy;
	end
	always @(*) begin : _lambda__s_dut_controller_recv_from_cpu_pkt_queue_ctrl_send_val
		send_val = count > 2'd0;
	end
	always @(*) begin : _lambda__s_dut_controller_recv_from_cpu_pkt_queue_ctrl_send_xfer
		send_xfer = send_val & send_rdy;
	end
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(posedge clk) begin : up_reg
		if (reset) begin
			head <= 1'd0;
			tail <= 1'd0;
			count <= 2'd0;
		end
		else begin
			if (recv_xfer)
				tail <= (tail < (sv2v_cast_1(__const__num_entries_at_up_reg) - 1'd1) ? tail + 1'd1 : 1'd0);
			if (send_xfer)
				head <= (head < (sv2v_cast_1(__const__num_entries_at_up_reg) - 1'd1) ? head + 1'd1 : 1'd0);
			if (recv_xfer & ~send_xfer)
				count <= count + 2'd1;
			else if (~recv_xfer & send_xfer)
				count <= count - 2'd1;
		end
	end
	assign wen = recv_xfer;
	assign waddr = tail;
	assign raddr = head;
endmodule
module RegisterFile__25f6b6a6d2e7f424 (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	output reg [207:0] rdata;
	input wire [0:0] reset;
	input wire [0:0] waddr;
	input wire [207:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [207:0] regs [0:1];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 208+:208] = regs[raddr[sv2v_cast_1(i)+:1]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i)+:1]] <= wdata[sv2v_cast_1(i) * 208+:208];
		end
	end
endmodule
module NormalQueueDpathRTL__55c6fcde46462f0c (
	clk,
	raddr,
	recv_msg,
	reset,
	send_msg,
	waddr,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	input wire [207:0] recv_msg;
	input wire [0:0] reset;
	output wire [207:0] send_msg;
	input wire [0:0] waddr;
	input wire [0:0] wen;
	wire [0:0] rf__clk;
	wire [0:0] rf__raddr;
	wire [207:0] rf__rdata;
	wire [0:0] rf__reset;
	wire [0:0] rf__waddr;
	wire [207:0] rf__wdata;
	wire [0:0] rf__wen;
	RegisterFile__25f6b6a6d2e7f424 rf(
		.clk(rf__clk),
		.raddr(rf__raddr),
		.rdata(rf__rdata),
		.reset(rf__reset),
		.waddr(rf__waddr),
		.wdata(rf__wdata),
		.wen(rf__wen)
	);
	assign rf__clk = clk;
	assign rf__reset = reset;
	assign rf__raddr[0+:1] = raddr;
	assign send_msg = rf__rdata[0+:208];
	assign rf__wen[0+:1] = wen;
	assign rf__waddr[0+:1] = waddr;
	assign rf__wdata[0+:208] = recv_msg;
endmodule
module NormalQueueRTL__55c6fcde46462f0c (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1:0] count;
	input wire [0:0] reset;
	input wire [207:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [207:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] ctrl__clk;
	wire [1:0] ctrl__count;
	wire [0:0] ctrl__raddr;
	wire [0:0] ctrl__recv_rdy;
	wire [0:0] ctrl__recv_val;
	wire [0:0] ctrl__reset;
	wire [0:0] ctrl__send_rdy;
	wire [0:0] ctrl__send_val;
	wire [0:0] ctrl__waddr;
	wire [0:0] ctrl__wen;
	NormalQueueCtrlRTL__num_entries_2 ctrl(
		.clk(ctrl__clk),
		.count(ctrl__count),
		.raddr(ctrl__raddr),
		.recv_rdy(ctrl__recv_rdy),
		.recv_val(ctrl__recv_val),
		.reset(ctrl__reset),
		.send_rdy(ctrl__send_rdy),
		.send_val(ctrl__send_val),
		.waddr(ctrl__waddr),
		.wen(ctrl__wen)
	);
	wire [0:0] dpath__clk;
	wire [0:0] dpath__raddr;
	wire [207:0] dpath__recv_msg;
	wire [0:0] dpath__reset;
	wire [207:0] dpath__send_msg;
	wire [0:0] dpath__waddr;
	wire [0:0] dpath__wen;
	NormalQueueDpathRTL__55c6fcde46462f0c dpath(
		.clk(dpath__clk),
		.raddr(dpath__raddr),
		.recv_msg(dpath__recv_msg),
		.reset(dpath__reset),
		.send_msg(dpath__send_msg),
		.waddr(dpath__waddr),
		.wen(dpath__wen)
	);
	assign ctrl__clk = clk;
	assign ctrl__reset = reset;
	assign dpath__clk = clk;
	assign dpath__reset = reset;
	assign dpath__wen = ctrl__wen;
	assign dpath__waddr = ctrl__waddr;
	assign dpath__raddr = ctrl__raddr;
	assign ctrl__recv_val = recv__val;
	assign recv__rdy = ctrl__recv_rdy;
	assign dpath__recv_msg = recv__msg;
	assign send__val = ctrl__send_val;
	assign ctrl__send_rdy = send__rdy;
	assign send__msg = dpath__send_msg;
	assign count = ctrl__count;
endmodule
module RegisterFile__c1557596a72966ef (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	output reg [208:0] rdata;
	input wire [0:0] reset;
	input wire [0:0] waddr;
	input wire [208:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [208:0] regs [0:1];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 209+:209] = regs[raddr[sv2v_cast_1(i)+:1]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i)+:1]] <= wdata[sv2v_cast_1(i) * 209+:209];
		end
	end
endmodule
module NormalQueueDpathRTL__fe5ccad25ef685a2 (
	clk,
	raddr,
	recv_msg,
	reset,
	send_msg,
	waddr,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	input wire [208:0] recv_msg;
	input wire [0:0] reset;
	output wire [208:0] send_msg;
	input wire [0:0] waddr;
	input wire [0:0] wen;
	wire [0:0] rf__clk;
	wire [0:0] rf__raddr;
	wire [208:0] rf__rdata;
	wire [0:0] rf__reset;
	wire [0:0] rf__waddr;
	wire [208:0] rf__wdata;
	wire [0:0] rf__wen;
	RegisterFile__c1557596a72966ef rf(
		.clk(rf__clk),
		.raddr(rf__raddr),
		.rdata(rf__rdata),
		.reset(rf__reset),
		.waddr(rf__waddr),
		.wdata(rf__wdata),
		.wen(rf__wen)
	);
	assign rf__clk = clk;
	assign rf__reset = reset;
	assign rf__raddr[0+:1] = raddr;
	assign send_msg = rf__rdata[0+:209];
	assign rf__wen[0+:1] = wen;
	assign rf__waddr[0+:1] = waddr;
	assign rf__wdata[0+:209] = recv_msg;
endmodule
module NormalQueueRTL__fe5ccad25ef685a2 (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1:0] count;
	input wire [0:0] reset;
	input wire [208:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [208:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] ctrl__clk;
	wire [1:0] ctrl__count;
	wire [0:0] ctrl__raddr;
	wire [0:0] ctrl__recv_rdy;
	wire [0:0] ctrl__recv_val;
	wire [0:0] ctrl__reset;
	wire [0:0] ctrl__send_rdy;
	wire [0:0] ctrl__send_val;
	wire [0:0] ctrl__waddr;
	wire [0:0] ctrl__wen;
	NormalQueueCtrlRTL__num_entries_2 ctrl(
		.clk(ctrl__clk),
		.count(ctrl__count),
		.raddr(ctrl__raddr),
		.recv_rdy(ctrl__recv_rdy),
		.recv_val(ctrl__recv_val),
		.reset(ctrl__reset),
		.send_rdy(ctrl__send_rdy),
		.send_val(ctrl__send_val),
		.waddr(ctrl__waddr),
		.wen(ctrl__wen)
	);
	wire [0:0] dpath__clk;
	wire [0:0] dpath__raddr;
	wire [208:0] dpath__recv_msg;
	wire [0:0] dpath__reset;
	wire [208:0] dpath__send_msg;
	wire [0:0] dpath__waddr;
	wire [0:0] dpath__wen;
	NormalQueueDpathRTL__fe5ccad25ef685a2 dpath(
		.clk(dpath__clk),
		.raddr(dpath__raddr),
		.recv_msg(dpath__recv_msg),
		.reset(dpath__reset),
		.send_msg(dpath__send_msg),
		.waddr(dpath__waddr),
		.wen(dpath__wen)
	);
	assign ctrl__clk = clk;
	assign ctrl__reset = reset;
	assign dpath__clk = clk;
	assign dpath__reset = reset;
	assign dpath__wen = ctrl__wen;
	assign dpath__waddr = ctrl__waddr;
	assign dpath__raddr = ctrl__raddr;
	assign ctrl__recv_val = recv__val;
	assign recv__rdy = ctrl__recv_rdy;
	assign dpath__recv_msg = recv__msg;
	assign send__val = ctrl__send_val;
	assign ctrl__send_rdy = send__rdy;
	assign send__msg = dpath__send_msg;
	assign count = ctrl__count;
endmodule
module ChannelRTL__582ded2d2397252e (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [208:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [208:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] queues__clk [0:0];
	wire [1:0] queues__count [0:0];
	wire [0:0] queues__reset [0:0];
	wire [208:0] queues__recv__msg [0:0];
	wire [0:0] queues__recv__rdy [0:0];
	wire [0:0] queues__recv__val [0:0];
	wire [208:0] queues__send__msg [0:0];
	wire [0:0] queues__send__rdy [0:0];
	wire [0:0] queues__send__val [0:0];
	NormalQueueRTL__fe5ccad25ef685a2 queues__0(
		.clk(queues__clk[0]),
		.count(queues__count[0]),
		.reset(queues__reset[0]),
		.recv__msg(queues__recv__msg[0]),
		.recv__rdy(queues__recv__rdy[0]),
		.recv__val(queues__recv__val[0]),
		.send__msg(queues__send__msg[0]),
		.send__rdy(queues__send__rdy[0]),
		.send__val(queues__send__val[0])
	);
	assign queues__clk[0] = clk;
	assign queues__reset[0] = reset;
	assign queues__recv__msg[0] = recv__msg;
	assign recv__rdy = queues__recv__rdy[0];
	assign queues__recv__val[0] = recv__val;
	assign send__msg = queues__send__msg[0];
	assign queues__send__rdy[0] = send__rdy;
	assign send__val = queues__send__val[0];
endmodule
module ControllerRTL__8a6408c51f9d4265 (
	cgra_id,
	clk,
	reset,
	recv_from_cpu_pkt__msg,
	recv_from_cpu_pkt__rdy,
	recv_from_cpu_pkt__val,
	recv_from_ctrl_ring_pkt__msg,
	recv_from_ctrl_ring_pkt__rdy,
	recv_from_ctrl_ring_pkt__val,
	recv_from_inter_cgra_noc__msg,
	recv_from_inter_cgra_noc__rdy,
	recv_from_inter_cgra_noc__val,
	recv_from_tile_load_request_pkt__msg,
	recv_from_tile_load_request_pkt__rdy,
	recv_from_tile_load_request_pkt__val,
	recv_from_tile_load_response_pkt__msg,
	recv_from_tile_load_response_pkt__rdy,
	recv_from_tile_load_response_pkt__val,
	recv_from_tile_store_request_pkt__msg,
	recv_from_tile_store_request_pkt__rdy,
	recv_from_tile_store_request_pkt__val,
	send_to_cpu_pkt__msg,
	send_to_cpu_pkt__rdy,
	send_to_cpu_pkt__val,
	send_to_ctrl_ring_pkt__msg,
	send_to_ctrl_ring_pkt__rdy,
	send_to_ctrl_ring_pkt__val,
	send_to_inter_cgra_noc__msg,
	send_to_inter_cgra_noc__rdy,
	send_to_inter_cgra_noc__val,
	send_to_mem_load_request__msg,
	send_to_mem_load_request__rdy,
	send_to_mem_load_request__val,
	send_to_mem_store_request__msg,
	send_to_mem_store_request__rdy,
	send_to_mem_store_request__val,
	send_to_tile_load_response__msg,
	send_to_tile_load_response__rdy,
	send_to_tile_load_response__val
);
	input wire [1:0] cgra_id;
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [207:0] recv_from_cpu_pkt__msg;
	output wire [0:0] recv_from_cpu_pkt__rdy;
	input wire [0:0] recv_from_cpu_pkt__val;
	input wire [207:0] recv_from_ctrl_ring_pkt__msg;
	output reg [0:0] recv_from_ctrl_ring_pkt__rdy;
	input wire [0:0] recv_from_ctrl_ring_pkt__val;
	input wire [208:0] recv_from_inter_cgra_noc__msg;
	output reg [0:0] recv_from_inter_cgra_noc__rdy;
	input wire [0:0] recv_from_inter_cgra_noc__val;
	input wire [208:0] recv_from_tile_load_request_pkt__msg;
	output wire [0:0] recv_from_tile_load_request_pkt__rdy;
	input wire [0:0] recv_from_tile_load_request_pkt__val;
	input wire [208:0] recv_from_tile_load_response_pkt__msg;
	output wire [0:0] recv_from_tile_load_response_pkt__rdy;
	input wire [0:0] recv_from_tile_load_response_pkt__val;
	input wire [208:0] recv_from_tile_store_request_pkt__msg;
	output wire [0:0] recv_from_tile_store_request_pkt__rdy;
	input wire [0:0] recv_from_tile_store_request_pkt__val;
	output wire [207:0] send_to_cpu_pkt__msg;
	input wire [0:0] send_to_cpu_pkt__rdy;
	output wire [0:0] send_to_cpu_pkt__val;
	output reg [207:0] send_to_ctrl_ring_pkt__msg;
	input wire [0:0] send_to_ctrl_ring_pkt__rdy;
	output reg [0:0] send_to_ctrl_ring_pkt__val;
	output reg [208:0] send_to_inter_cgra_noc__msg;
	input wire [0:0] send_to_inter_cgra_noc__rdy;
	output reg [0:0] send_to_inter_cgra_noc__val;
	output wire [208:0] send_to_mem_load_request__msg;
	input wire [0:0] send_to_mem_load_request__rdy;
	output wire [0:0] send_to_mem_load_request__val;
	output wire [208:0] send_to_mem_store_request__msg;
	input wire [0:0] send_to_mem_store_request__rdy;
	output wire [0:0] send_to_mem_store_request__val;
	output wire [208:0] send_to_tile_load_response__msg;
	input wire [0:0] send_to_tile_load_response__rdy;
	output wire [0:0] send_to_tile_load_response__val;
	localparam [2:0] __const__num_tiles_at_update_received_msg = 3'd4;
	localparam [3:0] __const__CMD_LOAD_REQUEST = 4'd10;
	localparam [3:0] __const__CMD_STORE_REQUEST = 4'd12;
	localparam [3:0] __const__CMD_LOAD_RESPONSE = 4'd11;
	localparam [3:0] __const__CMD_COMPLETE = 4'd14;
	localparam [1:0] __const__CMD_CONFIG = 2'd3;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_FU = 3'd4;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR = 3'd5;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR = 3'd6;
	localparam [2:0] __const__CMD_CONFIG_TOTAL_CTRL_COUNT = 3'd7;
	localparam [3:0] __const__CMD_CONFIG_COUNT_PER_ITER = 4'd8;
	localparam [3:0] __const__CMD_CONST = 4'd13;
	localparam [0:0] __const__CMD_LAUNCH = 1'd0;
	localparam [1:0] __const__addr_offset_nbits_at_update_sending_to_noc_msg = 2'd2;
	wire [1:0] addr2controller_lut [0:3];
	wire [1:0] idTo2d_x_lut [0:3];
	wire [0:0] idTo2d_y_lut [0:3];
	wire [0:0] crossbar__clk;
	wire [1049:0] crossbar__packet_on_input_units;
	wire [0:0] crossbar__reset;
	reg [1049:0] crossbar__recv__msg;
	wire [4:0] crossbar__recv__rdy;
	reg [4:0] crossbar__recv__val;
	wire [209:0] crossbar__send__msg;
	reg [0:0] crossbar__send__rdy;
	wire [0:0] crossbar__send__val;
	XbarBypassQueueRTL__cf118fbc1901d815 crossbar(
		.clk(crossbar__clk),
		.packet_on_input_units(crossbar__packet_on_input_units),
		.reset(crossbar__reset),
		.recv__msg(crossbar__recv__msg),
		.recv__rdy(crossbar__recv__rdy),
		.recv__val(crossbar__recv__val),
		.send__msg(crossbar__send__msg),
		.send__rdy(crossbar__send__rdy),
		.send__val(crossbar__send__val)
	);
	wire [0:0] recv_from_cpu_pkt_queue__clk;
	wire [1:0] recv_from_cpu_pkt_queue__count;
	wire [0:0] recv_from_cpu_pkt_queue__reset;
	wire [207:0] recv_from_cpu_pkt_queue__recv__msg;
	wire [0:0] recv_from_cpu_pkt_queue__recv__rdy;
	wire [0:0] recv_from_cpu_pkt_queue__recv__val;
	wire [207:0] recv_from_cpu_pkt_queue__send__msg;
	reg [0:0] recv_from_cpu_pkt_queue__send__rdy;
	wire [0:0] recv_from_cpu_pkt_queue__send__val;
	NormalQueueRTL__55c6fcde46462f0c recv_from_cpu_pkt_queue(
		.clk(recv_from_cpu_pkt_queue__clk),
		.count(recv_from_cpu_pkt_queue__count),
		.reset(recv_from_cpu_pkt_queue__reset),
		.recv__msg(recv_from_cpu_pkt_queue__recv__msg),
		.recv__rdy(recv_from_cpu_pkt_queue__recv__rdy),
		.recv__val(recv_from_cpu_pkt_queue__recv__val),
		.send__msg(recv_from_cpu_pkt_queue__send__msg),
		.send__rdy(recv_from_cpu_pkt_queue__send__rdy),
		.send__val(recv_from_cpu_pkt_queue__send__val)
	);
	wire [0:0] recv_from_tile_load_request_pkt_queue__clk;
	wire [0:0] recv_from_tile_load_request_pkt_queue__reset;
	wire [208:0] recv_from_tile_load_request_pkt_queue__recv__msg;
	wire [0:0] recv_from_tile_load_request_pkt_queue__recv__rdy;
	wire [0:0] recv_from_tile_load_request_pkt_queue__recv__val;
	wire [208:0] recv_from_tile_load_request_pkt_queue__send__msg;
	reg [0:0] recv_from_tile_load_request_pkt_queue__send__rdy;
	wire [0:0] recv_from_tile_load_request_pkt_queue__send__val;
	ChannelRTL__582ded2d2397252e recv_from_tile_load_request_pkt_queue(
		.clk(recv_from_tile_load_request_pkt_queue__clk),
		.reset(recv_from_tile_load_request_pkt_queue__reset),
		.recv__msg(recv_from_tile_load_request_pkt_queue__recv__msg),
		.recv__rdy(recv_from_tile_load_request_pkt_queue__recv__rdy),
		.recv__val(recv_from_tile_load_request_pkt_queue__recv__val),
		.send__msg(recv_from_tile_load_request_pkt_queue__send__msg),
		.send__rdy(recv_from_tile_load_request_pkt_queue__send__rdy),
		.send__val(recv_from_tile_load_request_pkt_queue__send__val)
	);
	wire [0:0] recv_from_tile_load_response_pkt_queue__clk;
	wire [0:0] recv_from_tile_load_response_pkt_queue__reset;
	wire [208:0] recv_from_tile_load_response_pkt_queue__recv__msg;
	wire [0:0] recv_from_tile_load_response_pkt_queue__recv__rdy;
	wire [0:0] recv_from_tile_load_response_pkt_queue__recv__val;
	wire [208:0] recv_from_tile_load_response_pkt_queue__send__msg;
	reg [0:0] recv_from_tile_load_response_pkt_queue__send__rdy;
	wire [0:0] recv_from_tile_load_response_pkt_queue__send__val;
	ChannelRTL__582ded2d2397252e recv_from_tile_load_response_pkt_queue(
		.clk(recv_from_tile_load_response_pkt_queue__clk),
		.reset(recv_from_tile_load_response_pkt_queue__reset),
		.recv__msg(recv_from_tile_load_response_pkt_queue__recv__msg),
		.recv__rdy(recv_from_tile_load_response_pkt_queue__recv__rdy),
		.recv__val(recv_from_tile_load_response_pkt_queue__recv__val),
		.send__msg(recv_from_tile_load_response_pkt_queue__send__msg),
		.send__rdy(recv_from_tile_load_response_pkt_queue__send__rdy),
		.send__val(recv_from_tile_load_response_pkt_queue__send__val)
	);
	wire [0:0] recv_from_tile_store_request_pkt_queue__clk;
	wire [0:0] recv_from_tile_store_request_pkt_queue__reset;
	wire [208:0] recv_from_tile_store_request_pkt_queue__recv__msg;
	wire [0:0] recv_from_tile_store_request_pkt_queue__recv__rdy;
	wire [0:0] recv_from_tile_store_request_pkt_queue__recv__val;
	wire [208:0] recv_from_tile_store_request_pkt_queue__send__msg;
	reg [0:0] recv_from_tile_store_request_pkt_queue__send__rdy;
	wire [0:0] recv_from_tile_store_request_pkt_queue__send__val;
	ChannelRTL__582ded2d2397252e recv_from_tile_store_request_pkt_queue(
		.clk(recv_from_tile_store_request_pkt_queue__clk),
		.reset(recv_from_tile_store_request_pkt_queue__reset),
		.recv__msg(recv_from_tile_store_request_pkt_queue__recv__msg),
		.recv__rdy(recv_from_tile_store_request_pkt_queue__recv__rdy),
		.recv__val(recv_from_tile_store_request_pkt_queue__recv__val),
		.send__msg(recv_from_tile_store_request_pkt_queue__send__msg),
		.send__rdy(recv_from_tile_store_request_pkt_queue__send__rdy),
		.send__val(recv_from_tile_store_request_pkt_queue__send__val)
	);
	wire [0:0] send_to_cpu_pkt_queue__clk;
	wire [1:0] send_to_cpu_pkt_queue__count;
	wire [0:0] send_to_cpu_pkt_queue__reset;
	reg [207:0] send_to_cpu_pkt_queue__recv__msg;
	wire [0:0] send_to_cpu_pkt_queue__recv__rdy;
	reg [0:0] send_to_cpu_pkt_queue__recv__val;
	wire [207:0] send_to_cpu_pkt_queue__send__msg;
	wire [0:0] send_to_cpu_pkt_queue__send__rdy;
	wire [0:0] send_to_cpu_pkt_queue__send__val;
	NormalQueueRTL__55c6fcde46462f0c send_to_cpu_pkt_queue(
		.clk(send_to_cpu_pkt_queue__clk),
		.count(send_to_cpu_pkt_queue__count),
		.reset(send_to_cpu_pkt_queue__reset),
		.recv__msg(send_to_cpu_pkt_queue__recv__msg),
		.recv__rdy(send_to_cpu_pkt_queue__recv__rdy),
		.recv__val(send_to_cpu_pkt_queue__recv__val),
		.send__msg(send_to_cpu_pkt_queue__send__msg),
		.send__rdy(send_to_cpu_pkt_queue__send__rdy),
		.send__val(send_to_cpu_pkt_queue__send__val)
	);
	wire [0:0] send_to_mem_load_request_queue__clk;
	wire [0:0] send_to_mem_load_request_queue__reset;
	reg [208:0] send_to_mem_load_request_queue__recv__msg;
	wire [0:0] send_to_mem_load_request_queue__recv__rdy;
	reg [0:0] send_to_mem_load_request_queue__recv__val;
	wire [208:0] send_to_mem_load_request_queue__send__msg;
	wire [0:0] send_to_mem_load_request_queue__send__rdy;
	wire [0:0] send_to_mem_load_request_queue__send__val;
	ChannelRTL__582ded2d2397252e send_to_mem_load_request_queue(
		.clk(send_to_mem_load_request_queue__clk),
		.reset(send_to_mem_load_request_queue__reset),
		.recv__msg(send_to_mem_load_request_queue__recv__msg),
		.recv__rdy(send_to_mem_load_request_queue__recv__rdy),
		.recv__val(send_to_mem_load_request_queue__recv__val),
		.send__msg(send_to_mem_load_request_queue__send__msg),
		.send__rdy(send_to_mem_load_request_queue__send__rdy),
		.send__val(send_to_mem_load_request_queue__send__val)
	);
	wire [0:0] send_to_mem_store_request_queue__clk;
	wire [0:0] send_to_mem_store_request_queue__reset;
	reg [208:0] send_to_mem_store_request_queue__recv__msg;
	wire [0:0] send_to_mem_store_request_queue__recv__rdy;
	reg [0:0] send_to_mem_store_request_queue__recv__val;
	wire [208:0] send_to_mem_store_request_queue__send__msg;
	wire [0:0] send_to_mem_store_request_queue__send__rdy;
	wire [0:0] send_to_mem_store_request_queue__send__val;
	ChannelRTL__582ded2d2397252e send_to_mem_store_request_queue(
		.clk(send_to_mem_store_request_queue__clk),
		.reset(send_to_mem_store_request_queue__reset),
		.recv__msg(send_to_mem_store_request_queue__recv__msg),
		.recv__rdy(send_to_mem_store_request_queue__recv__rdy),
		.recv__val(send_to_mem_store_request_queue__recv__val),
		.send__msg(send_to_mem_store_request_queue__send__msg),
		.send__rdy(send_to_mem_store_request_queue__send__rdy),
		.send__val(send_to_mem_store_request_queue__send__val)
	);
	wire [0:0] send_to_tile_load_response_queue__clk;
	wire [0:0] send_to_tile_load_response_queue__reset;
	reg [208:0] send_to_tile_load_response_queue__recv__msg;
	wire [0:0] send_to_tile_load_response_queue__recv__rdy;
	reg [0:0] send_to_tile_load_response_queue__recv__val;
	wire [208:0] send_to_tile_load_response_queue__send__msg;
	wire [0:0] send_to_tile_load_response_queue__send__rdy;
	wire [0:0] send_to_tile_load_response_queue__send__val;
	ChannelRTL__582ded2d2397252e send_to_tile_load_response_queue(
		.clk(send_to_tile_load_response_queue__clk),
		.reset(send_to_tile_load_response_queue__reset),
		.recv__msg(send_to_tile_load_response_queue__recv__msg),
		.recv__rdy(send_to_tile_load_response_queue__recv__rdy),
		.recv__val(send_to_tile_load_response_queue__recv__val),
		.send__msg(send_to_tile_load_response_queue__send__msg),
		.send__rdy(send_to_tile_load_response_queue__send__rdy),
		.send__val(send_to_tile_load_response_queue__send__val)
	);
	reg [0:0] __tmpvar__update_received_msg_kLoadRequestInportIdx;
	reg [0:0] __tmpvar__update_received_msg_kLoadResponseInportIdx;
	reg [1:0] __tmpvar__update_received_msg_kStoreRequestInportIdx;
	reg [1:0] __tmpvar__update_received_msg_kFromCpuCtrlAndDataIdx;
	reg [2:0] __tmpvar__update_received_msg_kFromInterTileRingIdx;
	reg [208:0] __tmpvar__update_received_msg_received_pkt;
	reg [1:0] __tmpvar__update_sending_to_noc_msg_addr_dst_id;
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	always @(*) begin : update_received_msg
		__tmpvar__update_received_msg_kLoadRequestInportIdx = 1'd0;
		__tmpvar__update_received_msg_kLoadResponseInportIdx = 1'd1;
		__tmpvar__update_received_msg_kStoreRequestInportIdx = 2'd2;
		__tmpvar__update_received_msg_kFromCpuCtrlAndDataIdx = 2'd3;
		__tmpvar__update_received_msg_kFromInterTileRingIdx = 3'd4;
		send_to_cpu_pkt_queue__recv__val = 1'd0;
		send_to_cpu_pkt_queue__recv__msg = 208'h0000000000000000000000000000000000000000000000000000;
		recv_from_ctrl_ring_pkt__rdy = 1'd0;
		crossbar__recv__val[4 - __tmpvar__update_received_msg_kFromInterTileRingIdx+:1] = recv_from_ctrl_ring_pkt__val;
		recv_from_ctrl_ring_pkt__rdy = crossbar__recv__rdy[4 - __tmpvar__update_received_msg_kFromInterTileRingIdx+:1];
		crossbar__recv__msg[(4 - __tmpvar__update_received_msg_kFromInterTileRingIdx) * 210+:210] = {1'd0, cgra_id, recv_from_ctrl_ring_pkt__msg[199-:2], idTo2d_x_lut[cgra_id], idTo2d_y_lut[cgra_id], recv_from_ctrl_ring_pkt__msg[194-:2], recv_from_ctrl_ring_pkt__msg[192], recv_from_ctrl_ring_pkt__msg[207-:3], recv_from_ctrl_ring_pkt__msg[204-:3], 10'h000, recv_from_ctrl_ring_pkt__msg[182-:183]};
		crossbar__recv__val[4 - __tmpvar__update_received_msg_kLoadRequestInportIdx+:1] = recv_from_tile_load_request_pkt_queue__send__val;
		recv_from_tile_load_request_pkt_queue__send__rdy = crossbar__recv__rdy[4 - sv2v_cast_3(__tmpvar__update_received_msg_kLoadRequestInportIdx)+:1];
		crossbar__recv__msg[(4 - __tmpvar__update_received_msg_kLoadRequestInportIdx) * 210+:210] = {1'd0, recv_from_tile_load_request_pkt_queue__send__msg};
		crossbar__recv__val[4 - __tmpvar__update_received_msg_kStoreRequestInportIdx+:1] = recv_from_tile_store_request_pkt_queue__send__val;
		recv_from_tile_store_request_pkt_queue__send__rdy = crossbar__recv__rdy[4 - sv2v_cast_3(__tmpvar__update_received_msg_kStoreRequestInportIdx)+:1];
		crossbar__recv__msg[(4 - __tmpvar__update_received_msg_kStoreRequestInportIdx) * 210+:210] = {1'd0, recv_from_tile_store_request_pkt_queue__send__msg};
		crossbar__recv__val[4 - __tmpvar__update_received_msg_kLoadResponseInportIdx+:1] = recv_from_tile_load_response_pkt_queue__send__val;
		recv_from_tile_load_response_pkt_queue__send__rdy = crossbar__recv__rdy[4 - sv2v_cast_3(__tmpvar__update_received_msg_kLoadResponseInportIdx)+:1];
		crossbar__recv__msg[(4 - __tmpvar__update_received_msg_kLoadResponseInportIdx) * 210+:210] = {1'd0, recv_from_tile_load_response_pkt_queue__send__msg};
		crossbar__recv__val[4 - __tmpvar__update_received_msg_kFromCpuCtrlAndDataIdx+:1] = recv_from_cpu_pkt_queue__send__val;
		recv_from_cpu_pkt_queue__send__rdy = crossbar__recv__rdy[4 - sv2v_cast_3(__tmpvar__update_received_msg_kFromCpuCtrlAndDataIdx)+:1];
		crossbar__recv__msg[(4 - __tmpvar__update_received_msg_kFromCpuCtrlAndDataIdx) * 210+:210] = {1'd0, cgra_id, recv_from_cpu_pkt_queue__send__msg[199-:2], 3'h0, idTo2d_x_lut[recv_from_cpu_pkt_queue__send__msg[199-:2]], idTo2d_y_lut[recv_from_cpu_pkt_queue__send__msg[199-:2]], __const__num_tiles_at_update_received_msg, recv_from_cpu_pkt_queue__send__msg[204-:3], 10'h000, recv_from_cpu_pkt_queue__send__msg[182-:183]};
		send_to_mem_load_request_queue__recv__val = 1'd0;
		send_to_mem_store_request_queue__recv__val = 1'd0;
		send_to_tile_load_response_queue__recv__val = 1'd0;
		send_to_mem_load_request_queue__recv__msg = 209'h00000000000000000000000000000000000000000000000000000;
		send_to_mem_store_request_queue__recv__msg = 209'h00000000000000000000000000000000000000000000000000000;
		send_to_tile_load_response_queue__recv__msg = 209'h00000000000000000000000000000000000000000000000000000;
		recv_from_inter_cgra_noc__rdy = 1'd0;
		send_to_ctrl_ring_pkt__val = 1'd0;
		send_to_ctrl_ring_pkt__msg = 208'h0000000000000000000000000000000000000000000000000000;
		__tmpvar__update_received_msg_received_pkt = recv_from_inter_cgra_noc__msg;
		if (recv_from_inter_cgra_noc__val)
			if (recv_from_inter_cgra_noc__msg[182-:4] == __const__CMD_LOAD_REQUEST) begin
				send_to_mem_load_request_queue__recv__val = 1'd1;
				if (send_to_mem_load_request_queue__recv__rdy) begin
					recv_from_inter_cgra_noc__rdy = 1'd1;
					send_to_mem_load_request_queue__recv__msg = __tmpvar__update_received_msg_received_pkt;
				end
			end
			else if (recv_from_inter_cgra_noc__msg[182-:4] == __const__CMD_STORE_REQUEST) begin
				send_to_mem_store_request_queue__recv__msg = __tmpvar__update_received_msg_received_pkt;
				send_to_mem_store_request_queue__recv__val = 1'd1;
				if (send_to_mem_store_request_queue__recv__rdy)
					recv_from_inter_cgra_noc__rdy = 1'd1;
			end
			else if (recv_from_inter_cgra_noc__msg[182-:4] == __const__CMD_LOAD_RESPONSE) begin
				if (recv_from_inter_cgra_noc__msg[195-:3] == __const__num_tiles_at_update_received_msg) begin
					recv_from_inter_cgra_noc__rdy = send_to_cpu_pkt_queue__recv__rdy;
					send_to_cpu_pkt_queue__recv__val = 1'd1;
					send_to_cpu_pkt_queue__recv__msg = {recv_from_inter_cgra_noc__msg[198-:3], recv_from_inter_cgra_noc__msg[195-:3], recv_from_inter_cgra_noc__msg[208-:2], recv_from_inter_cgra_noc__msg[206-:2], recv_from_inter_cgra_noc__msg[204-:2], recv_from_inter_cgra_noc__msg[202], recv_from_inter_cgra_noc__msg[201-:2], recv_from_inter_cgra_noc__msg[199], 9'h000, recv_from_inter_cgra_noc__msg[182-:183]};
				end
				else begin
					recv_from_inter_cgra_noc__rdy = send_to_tile_load_response_queue__recv__rdy;
					send_to_tile_load_response_queue__recv__msg = __tmpvar__update_received_msg_received_pkt;
					send_to_tile_load_response_queue__recv__val = 1'd1;
				end
			end
			else if (recv_from_inter_cgra_noc__msg[182-:4] == __const__CMD_COMPLETE) begin
				recv_from_inter_cgra_noc__rdy = send_to_cpu_pkt_queue__recv__rdy;
				send_to_cpu_pkt_queue__recv__val = 1'd1;
				send_to_cpu_pkt_queue__recv__msg = {recv_from_inter_cgra_noc__msg[198-:3], recv_from_inter_cgra_noc__msg[195-:3], recv_from_inter_cgra_noc__msg[208-:2], recv_from_inter_cgra_noc__msg[206-:2], recv_from_inter_cgra_noc__msg[204-:2], recv_from_inter_cgra_noc__msg[202], recv_from_inter_cgra_noc__msg[201-:2], recv_from_inter_cgra_noc__msg[199], 9'h000, recv_from_inter_cgra_noc__msg[182-:183]};
			end
			else if ((((((((recv_from_inter_cgra_noc__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG)) | (recv_from_inter_cgra_noc__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU))) | (recv_from_inter_cgra_noc__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR))) | (recv_from_inter_cgra_noc__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR))) | (recv_from_inter_cgra_noc__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_TOTAL_CTRL_COUNT))) | (recv_from_inter_cgra_noc__msg[182-:4] == __const__CMD_CONFIG_COUNT_PER_ITER)) | (recv_from_inter_cgra_noc__msg[182-:4] == __const__CMD_CONST)) | (recv_from_inter_cgra_noc__msg[182-:4] == sv2v_cast_4(__const__CMD_LAUNCH))) begin
				recv_from_inter_cgra_noc__rdy = send_to_ctrl_ring_pkt__rdy;
				send_to_ctrl_ring_pkt__val = recv_from_inter_cgra_noc__val;
				send_to_ctrl_ring_pkt__msg = {recv_from_inter_cgra_noc__msg[198-:3], recv_from_inter_cgra_noc__msg[195-:3], recv_from_inter_cgra_noc__msg[208-:2], recv_from_inter_cgra_noc__msg[206-:2], recv_from_inter_cgra_noc__msg[204-:2], recv_from_inter_cgra_noc__msg[202], recv_from_inter_cgra_noc__msg[201-:2], recv_from_inter_cgra_noc__msg[199], 9'h000, recv_from_inter_cgra_noc__msg[182-:183]};
			end
	end
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : update_sending_to_noc_msg
		send_to_inter_cgra_noc__val = crossbar__send__val[1'd0+:1];
		crossbar__send__rdy[1'd0+:1] = send_to_inter_cgra_noc__rdy;
		send_to_inter_cgra_noc__msg = crossbar__send__msg[(1'd0 * 210) + 208-:209];
		if ((crossbar__send__msg[(1'd0 * 210) + 182-:4] == __const__CMD_LOAD_REQUEST) | (crossbar__send__msg[(1'd0 * 210) + 182-:4] == __const__CMD_STORE_REQUEST)) begin
			__tmpvar__update_sending_to_noc_msg_addr_dst_id = addr2controller_lut[sv2v_cast_2(crossbar__send__msg[(1'd0 * 210) + 143-:3] >> __const__addr_offset_nbits_at_update_sending_to_noc_msg)];
			send_to_inter_cgra_noc__msg[206-:2] = __tmpvar__update_sending_to_noc_msg_addr_dst_id;
			send_to_inter_cgra_noc__msg[201-:2] = idTo2d_x_lut[__tmpvar__update_sending_to_noc_msg_addr_dst_id];
			send_to_inter_cgra_noc__msg[199] = idTo2d_y_lut[__tmpvar__update_sending_to_noc_msg_addr_dst_id];
		end
	end
	assign recv_from_tile_load_request_pkt_queue__clk = clk;
	assign recv_from_tile_load_request_pkt_queue__reset = reset;
	assign recv_from_tile_load_response_pkt_queue__clk = clk;
	assign recv_from_tile_load_response_pkt_queue__reset = reset;
	assign recv_from_tile_store_request_pkt_queue__clk = clk;
	assign recv_from_tile_store_request_pkt_queue__reset = reset;
	assign send_to_mem_load_request_queue__clk = clk;
	assign send_to_mem_load_request_queue__reset = reset;
	assign send_to_tile_load_response_queue__clk = clk;
	assign send_to_tile_load_response_queue__reset = reset;
	assign send_to_mem_store_request_queue__clk = clk;
	assign send_to_mem_store_request_queue__reset = reset;
	assign crossbar__clk = clk;
	assign crossbar__reset = reset;
	assign recv_from_cpu_pkt_queue__clk = clk;
	assign recv_from_cpu_pkt_queue__reset = reset;
	assign send_to_cpu_pkt_queue__clk = clk;
	assign send_to_cpu_pkt_queue__reset = reset;
	assign addr2controller_lut[0] = 2'd0;
	assign addr2controller_lut[1] = 2'd1;
	assign addr2controller_lut[2] = 2'd2;
	assign addr2controller_lut[3] = 2'd3;
	assign idTo2d_x_lut[0] = 2'd0;
	assign idTo2d_y_lut[0] = 1'd0;
	assign idTo2d_x_lut[1] = 2'd1;
	assign idTo2d_y_lut[1] = 1'd0;
	assign idTo2d_x_lut[2] = 2'd2;
	assign idTo2d_y_lut[2] = 1'd0;
	assign idTo2d_x_lut[3] = 2'd3;
	assign idTo2d_y_lut[3] = 1'd0;
	assign recv_from_tile_load_request_pkt_queue__recv__msg = recv_from_tile_load_request_pkt__msg;
	assign recv_from_tile_load_request_pkt__rdy = recv_from_tile_load_request_pkt_queue__recv__rdy;
	assign recv_from_tile_load_request_pkt_queue__recv__val = recv_from_tile_load_request_pkt__val;
	assign recv_from_tile_load_response_pkt_queue__recv__msg = recv_from_tile_load_response_pkt__msg;
	assign recv_from_tile_load_response_pkt__rdy = recv_from_tile_load_response_pkt_queue__recv__rdy;
	assign recv_from_tile_load_response_pkt_queue__recv__val = recv_from_tile_load_response_pkt__val;
	assign recv_from_tile_store_request_pkt_queue__recv__msg = recv_from_tile_store_request_pkt__msg;
	assign recv_from_tile_store_request_pkt__rdy = recv_from_tile_store_request_pkt_queue__recv__rdy;
	assign recv_from_tile_store_request_pkt_queue__recv__val = recv_from_tile_store_request_pkt__val;
	assign send_to_mem_load_request__msg = send_to_mem_load_request_queue__send__msg;
	assign send_to_mem_load_request_queue__send__rdy = send_to_mem_load_request__rdy;
	assign send_to_mem_load_request__val = send_to_mem_load_request_queue__send__val;
	assign send_to_tile_load_response__msg = send_to_tile_load_response_queue__send__msg;
	assign send_to_tile_load_response_queue__send__rdy = send_to_tile_load_response__rdy;
	assign send_to_tile_load_response__val = send_to_tile_load_response_queue__send__val;
	assign send_to_mem_store_request__msg = send_to_mem_store_request_queue__send__msg;
	assign send_to_mem_store_request_queue__send__rdy = send_to_mem_store_request__rdy;
	assign send_to_mem_store_request__val = send_to_mem_store_request_queue__send__val;
	assign recv_from_cpu_pkt_queue__recv__msg = recv_from_cpu_pkt__msg;
	assign recv_from_cpu_pkt__rdy = recv_from_cpu_pkt_queue__recv__rdy;
	assign recv_from_cpu_pkt_queue__recv__val = recv_from_cpu_pkt__val;
	assign send_to_cpu_pkt__msg = send_to_cpu_pkt_queue__send__msg;
	assign send_to_cpu_pkt_queue__send__rdy = send_to_cpu_pkt__rdy;
	assign send_to_cpu_pkt__val = send_to_cpu_pkt_queue__send__val;
endmodule
module Counter__Type_Bits2__reset_value_2 (
	clk,
	count,
	decr,
	incr,
	load,
	load_value,
	reset
);
	input wire [0:0] clk;
	output reg [1:0] count;
	input wire [0:0] decr;
	input wire [0:0] incr;
	input wire [0:0] load;
	input wire [1:0] load_value;
	input wire [0:0] reset;
	localparam [1:0] __const__reset_value_at_up_count = 2'd2;
	always @(posedge clk) begin : up_count
		if (reset)
			count <= __const__reset_value_at_up_count;
		else if (load)
			count <= load_value;
		else if (incr & ~decr)
			count <= count + 2'd1;
		else if (~incr & decr)
			count <= count - 2'd1;
	end
endmodule
module RecvRTL2CreditSendRTL__1c17f17a9a80ace5 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__en,
	send__msg,
	send__yum
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [207:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output reg [0:0] send__en;
	output wire [207:0] send__msg;
	input wire [1:0] send__yum;
	localparam [1:0] __const__vc_at_up_credit_send = 2'd2;
	localparam [1:0] __const__vc_at_up_counter_decr = 2'd2;
	wire [0:0] credit__clk [0:1];
	wire [1:0] credit__count [0:1];
	reg [0:0] credit__decr [0:1];
	wire [0:0] credit__incr [0:1];
	wire [0:0] credit__load [0:1];
	wire [1:0] credit__load_value [0:1];
	wire [0:0] credit__reset [0:1];
	Counter__Type_Bits2__reset_value_2 credit__0(
		.clk(credit__clk[0]),
		.count(credit__count[0]),
		.decr(credit__decr[0]),
		.incr(credit__incr[0]),
		.load(credit__load[0]),
		.load_value(credit__load_value[0]),
		.reset(credit__reset[0])
	);
	Counter__Type_Bits2__reset_value_2 credit__1(
		.clk(credit__clk[1]),
		.count(credit__count[1]),
		.decr(credit__decr[1]),
		.incr(credit__incr[1]),
		.load(credit__load[1]),
		.load_value(credit__load_value[1]),
		.reset(credit__reset[1])
	);
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_counter_decr
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_counter_decr; i = i + 1'd1)
				credit__decr[sv2v_cast_1(i)] = send__en & (sv2v_cast_1(i) == send__msg[183]);
		end
	end
	always @(*) begin : up_credit_send
		send__en = 1'd0;
		recv__rdy = 1'd0;
		if (recv__val) begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_credit_send; i = i + 1'd1)
				if ((sv2v_cast_1(i) == recv__msg[183]) & (credit__count[sv2v_cast_1(i)] > 2'd0)) begin
					send__en = 1'd1;
					recv__rdy = 1'd1;
				end
		end
	end
	assign credit__clk[0] = clk;
	assign credit__reset[0] = reset;
	assign credit__clk[1] = clk;
	assign credit__reset[1] = reset;
	assign send__msg = recv__msg;
	assign credit__incr[0] = send__yum[1+:1];
	assign credit__load[0] = 1'd0;
	assign credit__load_value[0] = 2'd0;
	assign credit__incr[1] = send__yum[0+:1];
	assign credit__load[1] = 1'd0;
	assign credit__load_value[1] = 2'd0;
endmodule
module InputUnitCreditRTL__2c0f4443f71b921d (
	clk,
	reset,
	recv__en,
	recv__msg,
	recv__yum,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [0:0] recv__en;
	input wire [207:0] recv__msg;
	output reg [1:0] recv__yum;
	output wire [415:0] send__msg;
	input wire [1:0] send__rdy;
	output wire [1:0] send__val;
	localparam [0:0] __const__i_at__lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_0_ = 1'd0;
	localparam [0:0] __const__i_at__lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_1_ = 1'd1;
	localparam [1:0] __const__vc_at_up_enq = 2'd2;
	wire [0:0] buffers__clk [0:1];
	wire [1:0] buffers__count [0:1];
	wire [0:0] buffers__reset [0:1];
	wire [207:0] buffers__recv__msg [0:1];
	wire [0:0] buffers__recv__rdy [0:1];
	reg [0:0] buffers__recv__val [0:1];
	wire [207:0] buffers__send__msg [0:1];
	wire [0:0] buffers__send__rdy [0:1];
	wire [0:0] buffers__send__val [0:1];
	NormalQueueRTL__55c6fcde46462f0c buffers__0(
		.clk(buffers__clk[0]),
		.count(buffers__count[0]),
		.reset(buffers__reset[0]),
		.recv__msg(buffers__recv__msg[0]),
		.recv__rdy(buffers__recv__rdy[0]),
		.recv__val(buffers__recv__val[0]),
		.send__msg(buffers__send__msg[0]),
		.send__rdy(buffers__send__rdy[0]),
		.send__val(buffers__send__val[0])
	);
	NormalQueueRTL__55c6fcde46462f0c buffers__1(
		.clk(buffers__clk[1]),
		.count(buffers__count[1]),
		.reset(buffers__reset[1]),
		.recv__msg(buffers__recv__msg[1]),
		.recv__rdy(buffers__recv__rdy[1]),
		.recv__val(buffers__recv__val[1]),
		.send__msg(buffers__send__msg[1]),
		.send__rdy(buffers__send__rdy[1]),
		.send__val(buffers__send__val[1])
	);
	always @(*) begin : _lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_0_
		recv__yum[(1 - 1'd0) + 0+:1] = send__val[1 - __const__i_at__lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_0_+:1] & send__rdy[1 - __const__i_at__lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_0_+:1];
	end
	always @(*) begin : _lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_1_
		recv__yum[(1 - 1'd1) + 0+:1] = send__val[1 - __const__i_at__lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_1_+:1] & send__rdy[1 - __const__i_at__lambda__s_dut_ctrl_ring_routers_0__input_units_0__recv_yum_1_+:1];
	end
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_enq
		if (recv__en) begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_enq; i = i + 1'd1)
				buffers__recv__val[sv2v_cast_1(i)] = recv__msg[183] == sv2v_cast_1(i);
		end
		else begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_enq; i = i + 1'd1)
				buffers__recv__val[sv2v_cast_1(i)] = 1'd0;
		end
	end
	assign buffers__clk[0] = clk;
	assign buffers__reset[0] = reset;
	assign buffers__clk[1] = clk;
	assign buffers__reset[1] = reset;
	assign buffers__recv__msg[0] = recv__msg;
	assign send__msg[208+:208] = buffers__send__msg[0];
	assign buffers__send__rdy[0] = send__rdy[1+:1];
	assign send__val[1+:1] = buffers__send__val[0];
	assign buffers__recv__msg[1] = recv__msg;
	assign send__msg[0+:208] = buffers__send__msg[1];
	assign buffers__send__rdy[1] = send__rdy[0+:1];
	assign send__val[0+:1] = buffers__send__val[1];
endmodule
module OutputUnitCreditRTL__1c17f17a9a80ace5 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__en,
	send__msg,
	send__yum
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [207:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output reg [0:0] send__en;
	output wire [207:0] send__msg;
	input wire [1:0] send__yum;
	localparam [1:0] __const__vc_at_up_credit_send = 2'd2;
	localparam [1:0] __const__vc_at_up_counter_decr = 2'd2;
	wire [0:0] credit__clk [0:1];
	wire [1:0] credit__count [0:1];
	reg [0:0] credit__decr [0:1];
	wire [0:0] credit__incr [0:1];
	wire [0:0] credit__load [0:1];
	wire [1:0] credit__load_value [0:1];
	wire [0:0] credit__reset [0:1];
	Counter__Type_Bits2__reset_value_2 credit__0(
		.clk(credit__clk[0]),
		.count(credit__count[0]),
		.decr(credit__decr[0]),
		.incr(credit__incr[0]),
		.load(credit__load[0]),
		.load_value(credit__load_value[0]),
		.reset(credit__reset[0])
	);
	Counter__Type_Bits2__reset_value_2 credit__1(
		.clk(credit__clk[1]),
		.count(credit__count[1]),
		.decr(credit__decr[1]),
		.incr(credit__incr[1]),
		.load(credit__load[1]),
		.load_value(credit__load_value[1]),
		.reset(credit__reset[1])
	);
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_counter_decr
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_counter_decr; i = i + 1'd1)
				credit__decr[sv2v_cast_1(i)] = send__en & (sv2v_cast_1(i) == send__msg[183]);
		end
	end
	always @(*) begin : up_credit_send
		send__en = 1'd0;
		recv__rdy = 1'd0;
		if (recv__val) begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_credit_send; i = i + 1'd1)
				if ((sv2v_cast_1(i) == recv__msg[183]) & (credit__count[sv2v_cast_1(i)] > 2'd0)) begin
					send__en = 1'd1;
					recv__rdy = 1'd1;
				end
		end
	end
	assign credit__clk[0] = clk;
	assign credit__reset[0] = reset;
	assign credit__clk[1] = clk;
	assign credit__reset[1] = reset;
	assign send__msg = recv__msg;
	assign credit__incr[0] = send__yum[1+:1];
	assign credit__load[0] = 1'd0;
	assign credit__load_value[0] = 2'd0;
	assign credit__incr[1] = send__yum[0+:1];
	assign credit__load[1] = 1'd0;
	assign credit__load_value[1] = 2'd0;
endmodule
module RingRouteUnitRTL__9b7719ff2f1d58a0 (
	clk,
	pos,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [2:0] pos;
	input wire [0:0] reset;
	input wire [207:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output reg [623:0] send__msg;
	input wire [2:0] send__rdy;
	output reg [2:0] send__val;
	localparam [1:0] __const__SELF = 2'd2;
	localparam [0:0] __const__LEFT = 1'd0;
	localparam [0:0] __const__RIGHT = 1'd1;
	reg [2:0] left_dist;
	reg [1:0] out_dir;
	reg [2:0] right_dist;
	reg [207:0] send_msg_wire;
	wire [2:0] send_rdy;
	always @(*) begin : up_left_right_dist
		if (recv__msg[204-:3] < pos) begin
			left_dist = pos - recv__msg[204-:3];
			right_dist = ((3'd4 - pos) + recv__msg[204-:3]) + 3'd1;
		end
		else begin
			left_dist = ((3'd1 + 3'd4) + pos) - recv__msg[204-:3];
			right_dist = recv__msg[204-:3] - pos;
		end
	end
	always @(*) begin : up_ru_recv_rdy
		recv__rdy = send_rdy[out_dir];
	end
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : up_ru_routing
		out_dir = 2'd0;
		send_msg_wire = recv__msg;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < 2'd3; i = i + 1'd1)
				begin
					send__val[2 - sv2v_cast_2(i)+:1] = 1'd0;
					send__msg[(2 - sv2v_cast_2(i)) * 208+:208] = recv__msg;
				end
		end
		if (recv__val) begin
			if (pos == recv__msg[204-:3])
				out_dir = __const__SELF;
			else if (left_dist < right_dist)
				out_dir = sv2v_cast_2(__const__LEFT);
			else
				out_dir = sv2v_cast_2(__const__RIGHT);
			if ((pos == 3'd4) & (out_dir == sv2v_cast_2(__const__RIGHT)))
				send_msg_wire[183] = 1'd1;
			else if ((pos == 3'd0) & (out_dir == sv2v_cast_2(__const__LEFT)))
				send_msg_wire[183] = 1'd1;
			send__val[2 - out_dir+:1] = 1'd1;
			send__msg[(2 - out_dir) * 208+:208] = send_msg_wire;
		end
	end
	assign send_rdy[0:0] = send__rdy[2+:1];
	assign send_rdy[1:1] = send__rdy[1+:1];
	assign send_rdy[2:2] = send__rdy[0+:1];
endmodule
module RegEnRst__Type_Bits6__reset_value_1 (
	clk,
	en,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	input wire [5:0] in_;
	output reg [5:0] out;
	input wire [0:0] reset;
	localparam [0:0] __const__reset_value_at_up_regenrst = 1'd1;
	function automatic [5:0] sv2v_cast_6;
		input reg [5:0] inp;
		sv2v_cast_6 = inp;
	endfunction
	always @(posedge clk) begin : up_regenrst
		if (reset)
			out <= sv2v_cast_6(__const__reset_value_at_up_regenrst);
		else if (en)
			out <= in_;
	end
endmodule
module RoundRobinArbiterEn__nreqs_6 (
	clk,
	en,
	grants,
	reqs,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	output reg [5:0] grants;
	input wire [5:0] reqs;
	input wire [0:0] reset;
	localparam [2:0] __const__nreqs_at_comb_reqs_int = 3'd6;
	localparam [3:0] __const__nreqsX2_at_comb_reqs_int = 4'd12;
	localparam [2:0] __const__nreqs_at_comb_grants = 3'd6;
	localparam [2:0] __const__nreqs_at_comb_priority_int = 3'd6;
	localparam [3:0] __const__nreqsX2_at_comb_priority_int = 4'd12;
	localparam [3:0] __const__nreqsX2_at_comb_kills = 4'd12;
	localparam [3:0] __const__nreqsX2_at_comb_grants_int = 4'd12;
	reg [11:0] grants_int;
	reg [12:0] kills;
	reg [0:0] priority_en;
	reg [11:0] priority_int;
	reg [11:0] reqs_int;
	wire [0:0] priority_reg__clk;
	wire [0:0] priority_reg__en;
	wire [5:0] priority_reg__in_;
	wire [5:0] priority_reg__out;
	wire [0:0] priority_reg__reset;
	RegEnRst__Type_Bits6__reset_value_1 priority_reg(
		.clk(priority_reg__clk),
		.en(priority_reg__en),
		.in_(priority_reg__in_),
		.out(priority_reg__out),
		.reset(priority_reg__reset)
	);
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	always @(*) begin : comb_grants
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqs_at_comb_grants; i = i + 1'd1)
				grants[sv2v_cast_3(i)] = grants_int[sv2v_cast_4(i)] | grants_int[sv2v_cast_4(__const__nreqs_at_comb_grants) + sv2v_cast_4(i)];
		end
	end
	always @(*) begin : comb_grants_int
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_grants_int; i = i + 1'd1)
				if (priority_int[sv2v_cast_4(i)])
					grants_int[sv2v_cast_4(i)] = reqs_int[sv2v_cast_4(i)];
				else
					grants_int[sv2v_cast_4(i)] = ~kills[sv2v_cast_4(i)] & reqs_int[sv2v_cast_4(i)];
		end
	end
	always @(*) begin : comb_kills
		kills[4'd0] = 1'd1;
		begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_kills; i = i + 1'd1)
				if (priority_int[sv2v_cast_4(i)])
					kills[sv2v_cast_4(i) + 4'd1] = reqs_int[sv2v_cast_4(i)];
				else
					kills[sv2v_cast_4(i) + 4'd1] = kills[sv2v_cast_4(i)] | (~kills[sv2v_cast_4(i)] & reqs_int[sv2v_cast_4(i)]);
		end
	end
	always @(*) begin : comb_priority_en
		priority_en = (grants != 6'd0) & en;
	end
	always @(*) begin : comb_priority_int
		priority_int[4'd5:4'd0] = priority_reg__out;
		priority_int[4'd11:sv2v_cast_4(__const__nreqs_at_comb_priority_int)] = 6'd0;
	end
	always @(*) begin : comb_reqs_int
		reqs_int[4'd5:4'd0] = reqs;
		reqs_int[4'd11:sv2v_cast_4(__const__nreqs_at_comb_reqs_int)] = reqs;
	end
	assign priority_reg__clk = clk;
	assign priority_reg__reset = reset;
	assign priority_reg__en = priority_en;
	assign priority_reg__in_[5:1] = grants[4:0];
	assign priority_reg__in_[0:0] = grants[5:5];
endmodule
module Encoder__in_nbits_6__out_nbits_3 (
	clk,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [5:0] in_;
	output reg [2:0] out;
	input wire [0:0] reset;
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : encode
		out = 3'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < 3'd6; i = i + 1'd1)
				if (in_[sv2v_cast_3(i)])
					out = sv2v_cast_3(i);
		end
	end
endmodule
module Mux__d8692e8eb4e13938 (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [1247:0] in_;
	output reg [207:0] out;
	input wire [0:0] reset;
	input wire [2:0] sel;
	always @(*) begin : up_mux
		out = in_[(5 - sel) * 208+:208];
	end
endmodule
module SwitchUnitRTL__66323cc3832ecd2a (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [1247:0] recv__msg;
	output reg [5:0] recv__rdy;
	input wire [5:0] recv__val;
	output wire [207:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	localparam [2:0] __const__num_inports_at_up_get_en = 3'd6;
	wire [0:0] arbiter__clk;
	wire [0:0] arbiter__en;
	wire [5:0] arbiter__grants;
	wire [5:0] arbiter__reqs;
	wire [0:0] arbiter__reset;
	RoundRobinArbiterEn__nreqs_6 arbiter(
		.clk(arbiter__clk),
		.en(arbiter__en),
		.grants(arbiter__grants),
		.reqs(arbiter__reqs),
		.reset(arbiter__reset)
	);
	wire [0:0] encoder__clk;
	wire [5:0] encoder__in_;
	wire [2:0] encoder__out;
	wire [0:0] encoder__reset;
	Encoder__in_nbits_6__out_nbits_3 encoder(
		.clk(encoder__clk),
		.in_(encoder__in_),
		.out(encoder__out),
		.reset(encoder__reset)
	);
	wire [0:0] mux__clk;
	wire [1247:0] mux__in_;
	wire [207:0] mux__out;
	wire [0:0] mux__reset;
	wire [2:0] mux__sel;
	Mux__d8692e8eb4e13938 mux(
		.clk(mux__clk),
		.in_(mux__in_),
		.out(mux__out),
		.reset(mux__reset),
		.sel(mux__sel)
	);
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : up_get_en
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_up_get_en; i = i + 1'd1)
				recv__rdy[5 - sv2v_cast_3(i)+:1] = send__rdy & (mux__sel == sv2v_cast_3(i));
		end
	end
	always @(*) begin : up_send_val
		send__val = arbiter__grants > 6'd0;
	end
	assign arbiter__clk = clk;
	assign arbiter__reset = reset;
	assign arbiter__en = 1'd1;
	assign mux__clk = clk;
	assign mux__reset = reset;
	assign send__msg = mux__out;
	assign encoder__clk = clk;
	assign encoder__reset = reset;
	assign encoder__in_ = arbiter__grants;
	assign mux__sel = encoder__out;
	assign arbiter__reqs[0:0] = recv__val[5+:1];
	assign mux__in_[1040+:208] = recv__msg[1040+:208];
	assign arbiter__reqs[1:1] = recv__val[4+:1];
	assign mux__in_[832+:208] = recv__msg[832+:208];
	assign arbiter__reqs[2:2] = recv__val[3+:1];
	assign mux__in_[624+:208] = recv__msg[624+:208];
	assign arbiter__reqs[3:3] = recv__val[2+:1];
	assign mux__in_[416+:208] = recv__msg[416+:208];
	assign arbiter__reqs[4:4] = recv__val[1+:1];
	assign mux__in_[208+:208] = recv__msg[208+:208];
	assign arbiter__reqs[5:5] = recv__val[0+:1];
	assign mux__in_[0+:208] = recv__msg[0+:208];
endmodule
module RingRouterRTL__aa12cf7d74338aa0 (
	clk,
	pos,
	reset,
	recv__en,
	recv__msg,
	recv__yum,
	send__en,
	send__msg,
	send__yum
);
	input wire [0:0] clk;
	input wire [2:0] pos;
	input wire [0:0] reset;
	input wire [2:0] recv__en;
	input wire [623:0] recv__msg;
	output wire [5:0] recv__yum;
	output wire [2:0] send__en;
	output wire [623:0] send__msg;
	input wire [5:0] send__yum;
	wire [0:0] input_units__clk [0:2];
	wire [0:0] input_units__reset [0:2];
	wire [0:0] input_units__recv__en [0:2];
	wire [207:0] input_units__recv__msg [0:2];
	wire [1:0] input_units__recv__yum [0:2];
	wire [415:0] input_units__send__msg [0:2];
	wire [1:0] input_units__send__rdy [0:2];
	wire [1:0] input_units__send__val [0:2];
	InputUnitCreditRTL__2c0f4443f71b921d input_units__0(
		.clk(input_units__clk[0]),
		.reset(input_units__reset[0]),
		.recv__en(input_units__recv__en[0]),
		.recv__msg(input_units__recv__msg[0]),
		.recv__yum(input_units__recv__yum[0]),
		.send__msg(input_units__send__msg[0]),
		.send__rdy(input_units__send__rdy[0]),
		.send__val(input_units__send__val[0])
	);
	InputUnitCreditRTL__2c0f4443f71b921d input_units__1(
		.clk(input_units__clk[1]),
		.reset(input_units__reset[1]),
		.recv__en(input_units__recv__en[1]),
		.recv__msg(input_units__recv__msg[1]),
		.recv__yum(input_units__recv__yum[1]),
		.send__msg(input_units__send__msg[1]),
		.send__rdy(input_units__send__rdy[1]),
		.send__val(input_units__send__val[1])
	);
	InputUnitCreditRTL__2c0f4443f71b921d input_units__2(
		.clk(input_units__clk[2]),
		.reset(input_units__reset[2]),
		.recv__en(input_units__recv__en[2]),
		.recv__msg(input_units__recv__msg[2]),
		.recv__yum(input_units__recv__yum[2]),
		.send__msg(input_units__send__msg[2]),
		.send__rdy(input_units__send__rdy[2]),
		.send__val(input_units__send__val[2])
	);
	wire [0:0] output_units__clk [0:2];
	wire [0:0] output_units__reset [0:2];
	wire [207:0] output_units__recv__msg [0:2];
	wire [0:0] output_units__recv__rdy [0:2];
	wire [0:0] output_units__recv__val [0:2];
	wire [0:0] output_units__send__en [0:2];
	wire [207:0] output_units__send__msg [0:2];
	wire [1:0] output_units__send__yum [0:2];
	OutputUnitCreditRTL__1c17f17a9a80ace5 output_units__0(
		.clk(output_units__clk[0]),
		.reset(output_units__reset[0]),
		.recv__msg(output_units__recv__msg[0]),
		.recv__rdy(output_units__recv__rdy[0]),
		.recv__val(output_units__recv__val[0]),
		.send__en(output_units__send__en[0]),
		.send__msg(output_units__send__msg[0]),
		.send__yum(output_units__send__yum[0])
	);
	OutputUnitCreditRTL__1c17f17a9a80ace5 output_units__1(
		.clk(output_units__clk[1]),
		.reset(output_units__reset[1]),
		.recv__msg(output_units__recv__msg[1]),
		.recv__rdy(output_units__recv__rdy[1]),
		.recv__val(output_units__recv__val[1]),
		.send__en(output_units__send__en[1]),
		.send__msg(output_units__send__msg[1]),
		.send__yum(output_units__send__yum[1])
	);
	OutputUnitCreditRTL__1c17f17a9a80ace5 output_units__2(
		.clk(output_units__clk[2]),
		.reset(output_units__reset[2]),
		.recv__msg(output_units__recv__msg[2]),
		.recv__rdy(output_units__recv__rdy[2]),
		.recv__val(output_units__recv__val[2]),
		.send__en(output_units__send__en[2]),
		.send__msg(output_units__send__msg[2]),
		.send__yum(output_units__send__yum[2])
	);
	wire [0:0] route_units__clk [0:5];
	wire [2:0] route_units__pos [0:5];
	wire [0:0] route_units__reset [0:5];
	wire [207:0] route_units__recv__msg [0:5];
	wire [0:0] route_units__recv__rdy [0:5];
	wire [0:0] route_units__recv__val [0:5];
	wire [623:0] route_units__send__msg [0:5];
	wire [2:0] route_units__send__rdy [0:5];
	wire [2:0] route_units__send__val [0:5];
	RingRouteUnitRTL__9b7719ff2f1d58a0 route_units__0(
		.clk(route_units__clk[0]),
		.pos(route_units__pos[0]),
		.reset(route_units__reset[0]),
		.recv__msg(route_units__recv__msg[0]),
		.recv__rdy(route_units__recv__rdy[0]),
		.recv__val(route_units__recv__val[0]),
		.send__msg(route_units__send__msg[0]),
		.send__rdy(route_units__send__rdy[0]),
		.send__val(route_units__send__val[0])
	);
	RingRouteUnitRTL__9b7719ff2f1d58a0 route_units__1(
		.clk(route_units__clk[1]),
		.pos(route_units__pos[1]),
		.reset(route_units__reset[1]),
		.recv__msg(route_units__recv__msg[1]),
		.recv__rdy(route_units__recv__rdy[1]),
		.recv__val(route_units__recv__val[1]),
		.send__msg(route_units__send__msg[1]),
		.send__rdy(route_units__send__rdy[1]),
		.send__val(route_units__send__val[1])
	);
	RingRouteUnitRTL__9b7719ff2f1d58a0 route_units__2(
		.clk(route_units__clk[2]),
		.pos(route_units__pos[2]),
		.reset(route_units__reset[2]),
		.recv__msg(route_units__recv__msg[2]),
		.recv__rdy(route_units__recv__rdy[2]),
		.recv__val(route_units__recv__val[2]),
		.send__msg(route_units__send__msg[2]),
		.send__rdy(route_units__send__rdy[2]),
		.send__val(route_units__send__val[2])
	);
	RingRouteUnitRTL__9b7719ff2f1d58a0 route_units__3(
		.clk(route_units__clk[3]),
		.pos(route_units__pos[3]),
		.reset(route_units__reset[3]),
		.recv__msg(route_units__recv__msg[3]),
		.recv__rdy(route_units__recv__rdy[3]),
		.recv__val(route_units__recv__val[3]),
		.send__msg(route_units__send__msg[3]),
		.send__rdy(route_units__send__rdy[3]),
		.send__val(route_units__send__val[3])
	);
	RingRouteUnitRTL__9b7719ff2f1d58a0 route_units__4(
		.clk(route_units__clk[4]),
		.pos(route_units__pos[4]),
		.reset(route_units__reset[4]),
		.recv__msg(route_units__recv__msg[4]),
		.recv__rdy(route_units__recv__rdy[4]),
		.recv__val(route_units__recv__val[4]),
		.send__msg(route_units__send__msg[4]),
		.send__rdy(route_units__send__rdy[4]),
		.send__val(route_units__send__val[4])
	);
	RingRouteUnitRTL__9b7719ff2f1d58a0 route_units__5(
		.clk(route_units__clk[5]),
		.pos(route_units__pos[5]),
		.reset(route_units__reset[5]),
		.recv__msg(route_units__recv__msg[5]),
		.recv__rdy(route_units__recv__rdy[5]),
		.recv__val(route_units__recv__val[5]),
		.send__msg(route_units__send__msg[5]),
		.send__rdy(route_units__send__rdy[5]),
		.send__val(route_units__send__val[5])
	);
	wire [0:0] switch_units__clk [0:2];
	wire [0:0] switch_units__reset [0:2];
	wire [1247:0] switch_units__recv__msg [0:2];
	wire [5:0] switch_units__recv__rdy [0:2];
	wire [5:0] switch_units__recv__val [0:2];
	wire [207:0] switch_units__send__msg [0:2];
	wire [0:0] switch_units__send__rdy [0:2];
	wire [0:0] switch_units__send__val [0:2];
	SwitchUnitRTL__66323cc3832ecd2a switch_units__0(
		.clk(switch_units__clk[0]),
		.reset(switch_units__reset[0]),
		.recv__msg(switch_units__recv__msg[0]),
		.recv__rdy(switch_units__recv__rdy[0]),
		.recv__val(switch_units__recv__val[0]),
		.send__msg(switch_units__send__msg[0]),
		.send__rdy(switch_units__send__rdy[0]),
		.send__val(switch_units__send__val[0])
	);
	SwitchUnitRTL__66323cc3832ecd2a switch_units__1(
		.clk(switch_units__clk[1]),
		.reset(switch_units__reset[1]),
		.recv__msg(switch_units__recv__msg[1]),
		.recv__rdy(switch_units__recv__rdy[1]),
		.recv__val(switch_units__recv__val[1]),
		.send__msg(switch_units__send__msg[1]),
		.send__rdy(switch_units__send__rdy[1]),
		.send__val(switch_units__send__val[1])
	);
	SwitchUnitRTL__66323cc3832ecd2a switch_units__2(
		.clk(switch_units__clk[2]),
		.reset(switch_units__reset[2]),
		.recv__msg(switch_units__recv__msg[2]),
		.recv__rdy(switch_units__recv__rdy[2]),
		.recv__val(switch_units__recv__val[2]),
		.send__msg(switch_units__send__msg[2]),
		.send__rdy(switch_units__send__rdy[2]),
		.send__val(switch_units__send__val[2])
	);
	assign input_units__clk[0] = clk;
	assign input_units__reset[0] = reset;
	assign input_units__clk[1] = clk;
	assign input_units__reset[1] = reset;
	assign input_units__clk[2] = clk;
	assign input_units__reset[2] = reset;
	assign route_units__clk[0] = clk;
	assign route_units__reset[0] = reset;
	assign route_units__clk[1] = clk;
	assign route_units__reset[1] = reset;
	assign route_units__clk[2] = clk;
	assign route_units__reset[2] = reset;
	assign route_units__clk[3] = clk;
	assign route_units__reset[3] = reset;
	assign route_units__clk[4] = clk;
	assign route_units__reset[4] = reset;
	assign route_units__clk[5] = clk;
	assign route_units__reset[5] = reset;
	assign switch_units__clk[0] = clk;
	assign switch_units__reset[0] = reset;
	assign switch_units__clk[1] = clk;
	assign switch_units__reset[1] = reset;
	assign switch_units__clk[2] = clk;
	assign switch_units__reset[2] = reset;
	assign output_units__clk[0] = clk;
	assign output_units__reset[0] = reset;
	assign output_units__clk[1] = clk;
	assign output_units__reset[1] = reset;
	assign output_units__clk[2] = clk;
	assign output_units__reset[2] = reset;
	assign input_units__recv__en[0] = recv__en[2+:1];
	assign input_units__recv__msg[0] = recv__msg[416+:208];
	assign recv__yum[5+:1] = input_units__recv__yum[0][1+:1];
	assign recv__yum[4+:1] = input_units__recv__yum[0][0+:1];
	assign route_units__recv__msg[0] = input_units__send__msg[0][208+:208];
	assign input_units__send__rdy[0][1+:1] = route_units__recv__rdy[0];
	assign route_units__recv__val[0] = input_units__send__val[0][1+:1];
	assign route_units__pos[0] = pos;
	assign route_units__recv__msg[1] = input_units__send__msg[0][0+:208];
	assign input_units__send__rdy[0][0+:1] = route_units__recv__rdy[1];
	assign route_units__recv__val[1] = input_units__send__val[0][0+:1];
	assign route_units__pos[1] = pos;
	assign input_units__recv__en[1] = recv__en[1+:1];
	assign input_units__recv__msg[1] = recv__msg[208+:208];
	assign recv__yum[3+:1] = input_units__recv__yum[1][1+:1];
	assign recv__yum[2+:1] = input_units__recv__yum[1][0+:1];
	assign route_units__recv__msg[2] = input_units__send__msg[1][208+:208];
	assign input_units__send__rdy[1][1+:1] = route_units__recv__rdy[2];
	assign route_units__recv__val[2] = input_units__send__val[1][1+:1];
	assign route_units__pos[2] = pos;
	assign route_units__recv__msg[3] = input_units__send__msg[1][0+:208];
	assign input_units__send__rdy[1][0+:1] = route_units__recv__rdy[3];
	assign route_units__recv__val[3] = input_units__send__val[1][0+:1];
	assign route_units__pos[3] = pos;
	assign input_units__recv__en[2] = recv__en[0+:1];
	assign input_units__recv__msg[2] = recv__msg[0+:208];
	assign recv__yum[1+:1] = input_units__recv__yum[2][1+:1];
	assign recv__yum[0+:1] = input_units__recv__yum[2][0+:1];
	assign route_units__recv__msg[4] = input_units__send__msg[2][208+:208];
	assign input_units__send__rdy[2][1+:1] = route_units__recv__rdy[4];
	assign route_units__recv__val[4] = input_units__send__val[2][1+:1];
	assign route_units__pos[4] = pos;
	assign route_units__recv__msg[5] = input_units__send__msg[2][0+:208];
	assign input_units__send__rdy[2][0+:1] = route_units__recv__rdy[5];
	assign route_units__recv__val[5] = input_units__send__val[2][0+:1];
	assign route_units__pos[5] = pos;
	assign switch_units__recv__msg[0][1040+:208] = route_units__send__msg[0][416+:208];
	assign route_units__send__rdy[0][2+:1] = switch_units__recv__rdy[0][5+:1];
	assign switch_units__recv__val[0][5+:1] = route_units__send__val[0][2+:1];
	assign switch_units__recv__msg[1][1040+:208] = route_units__send__msg[0][208+:208];
	assign route_units__send__rdy[0][1+:1] = switch_units__recv__rdy[1][5+:1];
	assign switch_units__recv__val[1][5+:1] = route_units__send__val[0][1+:1];
	assign switch_units__recv__msg[2][1040+:208] = route_units__send__msg[0][0+:208];
	assign route_units__send__rdy[0][0+:1] = switch_units__recv__rdy[2][5+:1];
	assign switch_units__recv__val[2][5+:1] = route_units__send__val[0][0+:1];
	assign switch_units__recv__msg[0][832+:208] = route_units__send__msg[1][416+:208];
	assign route_units__send__rdy[1][2+:1] = switch_units__recv__rdy[0][4+:1];
	assign switch_units__recv__val[0][4+:1] = route_units__send__val[1][2+:1];
	assign switch_units__recv__msg[1][832+:208] = route_units__send__msg[1][208+:208];
	assign route_units__send__rdy[1][1+:1] = switch_units__recv__rdy[1][4+:1];
	assign switch_units__recv__val[1][4+:1] = route_units__send__val[1][1+:1];
	assign switch_units__recv__msg[2][832+:208] = route_units__send__msg[1][0+:208];
	assign route_units__send__rdy[1][0+:1] = switch_units__recv__rdy[2][4+:1];
	assign switch_units__recv__val[2][4+:1] = route_units__send__val[1][0+:1];
	assign switch_units__recv__msg[0][624+:208] = route_units__send__msg[2][416+:208];
	assign route_units__send__rdy[2][2+:1] = switch_units__recv__rdy[0][3+:1];
	assign switch_units__recv__val[0][3+:1] = route_units__send__val[2][2+:1];
	assign switch_units__recv__msg[1][624+:208] = route_units__send__msg[2][208+:208];
	assign route_units__send__rdy[2][1+:1] = switch_units__recv__rdy[1][3+:1];
	assign switch_units__recv__val[1][3+:1] = route_units__send__val[2][1+:1];
	assign switch_units__recv__msg[2][624+:208] = route_units__send__msg[2][0+:208];
	assign route_units__send__rdy[2][0+:1] = switch_units__recv__rdy[2][3+:1];
	assign switch_units__recv__val[2][3+:1] = route_units__send__val[2][0+:1];
	assign switch_units__recv__msg[0][416+:208] = route_units__send__msg[3][416+:208];
	assign route_units__send__rdy[3][2+:1] = switch_units__recv__rdy[0][2+:1];
	assign switch_units__recv__val[0][2+:1] = route_units__send__val[3][2+:1];
	assign switch_units__recv__msg[1][416+:208] = route_units__send__msg[3][208+:208];
	assign route_units__send__rdy[3][1+:1] = switch_units__recv__rdy[1][2+:1];
	assign switch_units__recv__val[1][2+:1] = route_units__send__val[3][1+:1];
	assign switch_units__recv__msg[2][416+:208] = route_units__send__msg[3][0+:208];
	assign route_units__send__rdy[3][0+:1] = switch_units__recv__rdy[2][2+:1];
	assign switch_units__recv__val[2][2+:1] = route_units__send__val[3][0+:1];
	assign switch_units__recv__msg[0][208+:208] = route_units__send__msg[4][416+:208];
	assign route_units__send__rdy[4][2+:1] = switch_units__recv__rdy[0][1+:1];
	assign switch_units__recv__val[0][1+:1] = route_units__send__val[4][2+:1];
	assign switch_units__recv__msg[1][208+:208] = route_units__send__msg[4][208+:208];
	assign route_units__send__rdy[4][1+:1] = switch_units__recv__rdy[1][1+:1];
	assign switch_units__recv__val[1][1+:1] = route_units__send__val[4][1+:1];
	assign switch_units__recv__msg[2][208+:208] = route_units__send__msg[4][0+:208];
	assign route_units__send__rdy[4][0+:1] = switch_units__recv__rdy[2][1+:1];
	assign switch_units__recv__val[2][1+:1] = route_units__send__val[4][0+:1];
	assign switch_units__recv__msg[0][0+:208] = route_units__send__msg[5][416+:208];
	assign route_units__send__rdy[5][2+:1] = switch_units__recv__rdy[0][0+:1];
	assign switch_units__recv__val[0][0+:1] = route_units__send__val[5][2+:1];
	assign switch_units__recv__msg[1][0+:208] = route_units__send__msg[5][208+:208];
	assign route_units__send__rdy[5][1+:1] = switch_units__recv__rdy[1][0+:1];
	assign switch_units__recv__val[1][0+:1] = route_units__send__val[5][1+:1];
	assign switch_units__recv__msg[2][0+:208] = route_units__send__msg[5][0+:208];
	assign route_units__send__rdy[5][0+:1] = switch_units__recv__rdy[2][0+:1];
	assign switch_units__recv__val[2][0+:1] = route_units__send__val[5][0+:1];
	assign output_units__recv__msg[0] = switch_units__send__msg[0];
	assign switch_units__send__rdy[0] = output_units__recv__rdy[0];
	assign output_units__recv__val[0] = switch_units__send__val[0];
	assign send__en[2+:1] = output_units__send__en[0];
	assign send__msg[416+:208] = output_units__send__msg[0];
	assign output_units__send__yum[0][1+:1] = send__yum[5+:1];
	assign output_units__send__yum[0][0+:1] = send__yum[4+:1];
	assign output_units__recv__msg[1] = switch_units__send__msg[1];
	assign switch_units__send__rdy[1] = output_units__recv__rdy[1];
	assign output_units__recv__val[1] = switch_units__send__val[1];
	assign send__en[1+:1] = output_units__send__en[1];
	assign send__msg[208+:208] = output_units__send__msg[1];
	assign output_units__send__yum[1][1+:1] = send__yum[3+:1];
	assign output_units__send__yum[1][0+:1] = send__yum[2+:1];
	assign output_units__recv__msg[2] = switch_units__send__msg[2];
	assign switch_units__send__rdy[2] = output_units__recv__rdy[2];
	assign output_units__recv__val[2] = switch_units__send__val[2];
	assign send__en[0+:1] = output_units__send__en[2];
	assign send__msg[0+:208] = output_units__send__msg[2];
	assign output_units__send__yum[2][1+:1] = send__yum[1+:1];
	assign output_units__send__yum[2][0+:1] = send__yum[0+:1];
endmodule
module RegEnRst__Type_Bits2__reset_value_1 (
	clk,
	en,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	input wire [1:0] in_;
	output reg [1:0] out;
	input wire [0:0] reset;
	localparam [0:0] __const__reset_value_at_up_regenrst = 1'd1;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(posedge clk) begin : up_regenrst
		if (reset)
			out <= sv2v_cast_2(__const__reset_value_at_up_regenrst);
		else if (en)
			out <= in_;
	end
endmodule
module RoundRobinArbiterEn__nreqs_2 (
	clk,
	en,
	grants,
	reqs,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	output reg [1:0] grants;
	input wire [1:0] reqs;
	input wire [0:0] reset;
	localparam [1:0] __const__nreqs_at_comb_reqs_int = 2'd2;
	localparam [2:0] __const__nreqsX2_at_comb_reqs_int = 3'd4;
	localparam [1:0] __const__nreqs_at_comb_grants = 2'd2;
	localparam [1:0] __const__nreqs_at_comb_priority_int = 2'd2;
	localparam [2:0] __const__nreqsX2_at_comb_priority_int = 3'd4;
	localparam [2:0] __const__nreqsX2_at_comb_kills = 3'd4;
	localparam [2:0] __const__nreqsX2_at_comb_grants_int = 3'd4;
	reg [3:0] grants_int;
	reg [4:0] kills;
	reg [0:0] priority_en;
	reg [3:0] priority_int;
	reg [3:0] reqs_int;
	wire [0:0] priority_reg__clk;
	wire [0:0] priority_reg__en;
	wire [1:0] priority_reg__in_;
	wire [1:0] priority_reg__out;
	wire [0:0] priority_reg__reset;
	RegEnRst__Type_Bits2__reset_value_1 priority_reg(
		.clk(priority_reg__clk),
		.en(priority_reg__en),
		.in_(priority_reg__in_),
		.out(priority_reg__out),
		.reset(priority_reg__reset)
	);
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : comb_grants
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqs_at_comb_grants; i = i + 1'd1)
				grants[sv2v_cast_1(i)] = grants_int[sv2v_cast_2(i)] | grants_int[__const__nreqs_at_comb_grants + sv2v_cast_2(i)];
		end
	end
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : comb_grants_int
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_grants_int; i = i + 1'd1)
				if (priority_int[sv2v_cast_2(i)])
					grants_int[sv2v_cast_2(i)] = reqs_int[sv2v_cast_2(i)];
				else
					grants_int[sv2v_cast_2(i)] = ~kills[sv2v_cast_3(i)] & reqs_int[sv2v_cast_2(i)];
		end
	end
	always @(*) begin : comb_kills
		kills[3'd0] = 1'd1;
		begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_kills; i = i + 1'd1)
				if (priority_int[sv2v_cast_2(i)])
					kills[sv2v_cast_3(i) + 3'd1] = reqs_int[sv2v_cast_2(i)];
				else
					kills[sv2v_cast_3(i) + 3'd1] = kills[sv2v_cast_3(i)] | (~kills[sv2v_cast_3(i)] & reqs_int[sv2v_cast_2(i)]);
		end
	end
	always @(*) begin : comb_priority_en
		priority_en = (grants != 2'd0) & en;
	end
	always @(*) begin : comb_priority_int
		priority_int[2'd1:2'd0] = priority_reg__out;
		priority_int[2'd3:__const__nreqs_at_comb_priority_int] = 2'd0;
	end
	always @(*) begin : comb_reqs_int
		reqs_int[2'd1:2'd0] = reqs;
		reqs_int[2'd3:__const__nreqs_at_comb_reqs_int] = reqs;
	end
	assign priority_reg__clk = clk;
	assign priority_reg__reset = reset;
	assign priority_reg__en = priority_en;
	assign priority_reg__in_[1:1] = grants[0:0];
	assign priority_reg__in_[0:0] = grants[1:1];
endmodule
module Mux__8c374ece17386440 (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [415:0] in_;
	output reg [207:0] out;
	input wire [0:0] reset;
	input wire [0:0] sel;
	always @(*) begin : up_mux
		out = in_[(1 - sel) * 208+:208];
	end
endmodule
module BypassQueueDpathRTL__55c6fcde46462f0c (
	clk,
	mux_sel,
	raddr,
	recv_msg,
	reset,
	send_msg,
	waddr,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] mux_sel;
	input wire [0:0] raddr;
	input wire [207:0] recv_msg;
	input wire [0:0] reset;
	output wire [207:0] send_msg;
	input wire [0:0] waddr;
	input wire [0:0] wen;
	wire [0:0] mux__clk;
	wire [415:0] mux__in_;
	wire [207:0] mux__out;
	wire [0:0] mux__reset;
	wire [0:0] mux__sel;
	Mux__8c374ece17386440 mux(
		.clk(mux__clk),
		.in_(mux__in_),
		.out(mux__out),
		.reset(mux__reset),
		.sel(mux__sel)
	);
	wire [0:0] rf__clk;
	wire [0:0] rf__raddr;
	wire [207:0] rf__rdata;
	wire [0:0] rf__reset;
	wire [0:0] rf__waddr;
	wire [207:0] rf__wdata;
	wire [0:0] rf__wen;
	RegisterFile__25f6b6a6d2e7f424 rf(
		.clk(rf__clk),
		.raddr(rf__raddr),
		.rdata(rf__rdata),
		.reset(rf__reset),
		.waddr(rf__waddr),
		.wdata(rf__wdata),
		.wen(rf__wen)
	);
	assign rf__clk = clk;
	assign rf__reset = reset;
	assign rf__raddr[0+:1] = raddr;
	assign rf__wen[0+:1] = wen;
	assign rf__waddr[0+:1] = waddr;
	assign rf__wdata[0+:208] = recv_msg;
	assign mux__clk = clk;
	assign mux__reset = reset;
	assign mux__sel = mux_sel;
	assign mux__in_[208+:208] = rf__rdata[0+:208];
	assign mux__in_[0+:208] = recv_msg;
	assign send_msg = mux__out;
endmodule
module BypassQueueRTL__55c6fcde46462f0c (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1:0] count;
	input wire [0:0] reset;
	input wire [207:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [207:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] ctrl__clk;
	wire [1:0] ctrl__count;
	wire [0:0] ctrl__mux_sel;
	wire [0:0] ctrl__raddr;
	wire [0:0] ctrl__recv_rdy;
	wire [0:0] ctrl__recv_val;
	wire [0:0] ctrl__reset;
	wire [0:0] ctrl__send_rdy;
	wire [0:0] ctrl__send_val;
	wire [0:0] ctrl__waddr;
	wire [0:0] ctrl__wen;
	BypassQueueCtrlRTL__num_entries_2 ctrl(
		.clk(ctrl__clk),
		.count(ctrl__count),
		.mux_sel(ctrl__mux_sel),
		.raddr(ctrl__raddr),
		.recv_rdy(ctrl__recv_rdy),
		.recv_val(ctrl__recv_val),
		.reset(ctrl__reset),
		.send_rdy(ctrl__send_rdy),
		.send_val(ctrl__send_val),
		.waddr(ctrl__waddr),
		.wen(ctrl__wen)
	);
	wire [0:0] dpath__clk;
	wire [0:0] dpath__mux_sel;
	wire [0:0] dpath__raddr;
	wire [207:0] dpath__recv_msg;
	wire [0:0] dpath__reset;
	wire [207:0] dpath__send_msg;
	wire [0:0] dpath__waddr;
	wire [0:0] dpath__wen;
	BypassQueueDpathRTL__55c6fcde46462f0c dpath(
		.clk(dpath__clk),
		.mux_sel(dpath__mux_sel),
		.raddr(dpath__raddr),
		.recv_msg(dpath__recv_msg),
		.reset(dpath__reset),
		.send_msg(dpath__send_msg),
		.waddr(dpath__waddr),
		.wen(dpath__wen)
	);
	assign ctrl__clk = clk;
	assign ctrl__reset = reset;
	assign dpath__clk = clk;
	assign dpath__reset = reset;
	assign dpath__wen = ctrl__wen;
	assign dpath__waddr = ctrl__waddr;
	assign dpath__raddr = ctrl__raddr;
	assign dpath__mux_sel = ctrl__mux_sel;
	assign ctrl__recv_val = recv__val;
	assign recv__rdy = ctrl__recv_rdy;
	assign send__val = ctrl__send_val;
	assign ctrl__send_rdy = send__rdy;
	assign count = ctrl__count;
	assign dpath__recv_msg = recv__msg;
	assign send__msg = dpath__send_msg;
endmodule
module Encoder__in_nbits_2__out_nbits_1 (
	clk,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [1:0] in_;
	output reg [0:0] out;
	input wire [0:0] reset;
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : encode
		out = 1'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < 2'd2; i = i + 1'd1)
				if (in_[sv2v_cast_1(i)])
					out = sv2v_cast_1(i);
		end
	end
endmodule
module CreditRecvRTL2SendRTL__04ae6f3fc3c0287a (
	clk,
	reset,
	recv__en,
	recv__msg,
	recv__yum,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [0:0] recv__en;
	input wire [207:0] recv__msg;
	output reg [1:0] recv__yum;
	output reg [207:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	localparam [1:0] __const__vc_at_up_enq = 2'd2;
	localparam [1:0] __const__vc_at_up_deq_and_send = 2'd2;
	localparam [1:0] __const__vc_at_up_yummy = 2'd2;
	wire [0:0] arbiter__clk;
	wire [0:0] arbiter__en;
	wire [1:0] arbiter__grants;
	wire [1:0] arbiter__reqs;
	wire [0:0] arbiter__reset;
	RoundRobinArbiterEn__nreqs_2 arbiter(
		.clk(arbiter__clk),
		.en(arbiter__en),
		.grants(arbiter__grants),
		.reqs(arbiter__reqs),
		.reset(arbiter__reset)
	);
	wire [0:0] buffers__clk [0:1];
	wire [1:0] buffers__count [0:1];
	wire [0:0] buffers__reset [0:1];
	wire [207:0] buffers__recv__msg [0:1];
	wire [0:0] buffers__recv__rdy [0:1];
	reg [0:0] buffers__recv__val [0:1];
	wire [207:0] buffers__send__msg [0:1];
	reg [0:0] buffers__send__rdy [0:1];
	wire [0:0] buffers__send__val [0:1];
	BypassQueueRTL__55c6fcde46462f0c buffers__0(
		.clk(buffers__clk[0]),
		.count(buffers__count[0]),
		.reset(buffers__reset[0]),
		.recv__msg(buffers__recv__msg[0]),
		.recv__rdy(buffers__recv__rdy[0]),
		.recv__val(buffers__recv__val[0]),
		.send__msg(buffers__send__msg[0]),
		.send__rdy(buffers__send__rdy[0]),
		.send__val(buffers__send__val[0])
	);
	BypassQueueRTL__55c6fcde46462f0c buffers__1(
		.clk(buffers__clk[1]),
		.count(buffers__count[1]),
		.reset(buffers__reset[1]),
		.recv__msg(buffers__recv__msg[1]),
		.recv__rdy(buffers__recv__rdy[1]),
		.recv__val(buffers__recv__val[1]),
		.send__msg(buffers__send__msg[1]),
		.send__rdy(buffers__send__rdy[1]),
		.send__val(buffers__send__val[1])
	);
	wire [0:0] encoder__clk;
	wire [1:0] encoder__in_;
	wire [0:0] encoder__out;
	wire [0:0] encoder__reset;
	Encoder__in_nbits_2__out_nbits_1 encoder(
		.clk(encoder__clk),
		.in_(encoder__in_),
		.out(encoder__out),
		.reset(encoder__reset)
	);
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_deq_and_send
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_deq_and_send; i = i + 1'd1)
				buffers__send__rdy[sv2v_cast_1(i)] = 1'd0;
		end
		send__msg = buffers__send__msg[encoder__out];
		if (arbiter__grants > 2'd0) begin
			send__val = 1'd1;
			buffers__send__rdy[encoder__out] = send__rdy;
		end
		else
			send__val = 1'd0;
	end
	always @(*) begin : up_enq
		if (recv__en) begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_enq; i = i + 1'd1)
				buffers__recv__val[sv2v_cast_1(i)] = recv__msg[183] == sv2v_cast_1(i);
		end
		else begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_enq; i = i + 1'd1)
				buffers__recv__val[sv2v_cast_1(i)] = 1'd0;
		end
	end
	always @(*) begin : up_yummy
		begin : sv2v_autoblock_4
			reg [31:0] i;
			for (i = 1'd0; i < __const__vc_at_up_yummy; i = i + 1'd1)
				recv__yum[1 - sv2v_cast_1(i)+:1] = buffers__send__val[sv2v_cast_1(i)] & buffers__send__rdy[sv2v_cast_1(i)];
		end
	end
	assign buffers__clk[0] = clk;
	assign buffers__reset[0] = reset;
	assign buffers__clk[1] = clk;
	assign buffers__reset[1] = reset;
	assign arbiter__clk = clk;
	assign arbiter__reset = reset;
	assign encoder__clk = clk;
	assign encoder__reset = reset;
	assign buffers__recv__msg[0] = recv__msg;
	assign arbiter__reqs[0:0] = buffers__send__val[0];
	assign buffers__recv__msg[1] = recv__msg;
	assign arbiter__reqs[1:1] = buffers__send__val[1];
	assign encoder__in_ = arbiter__grants;
	assign arbiter__en = send__val;
endmodule
module RingNetworkRTL__79999f3d23637960 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [1039:0] recv__msg;
	output wire [4:0] recv__rdy;
	input wire [4:0] recv__val;
	output wire [1039:0] send__msg;
	input wire [4:0] send__rdy;
	output wire [4:0] send__val;
	wire [0:0] recv_adp__clk [0:4];
	wire [0:0] recv_adp__reset [0:4];
	wire [207:0] recv_adp__recv__msg [0:4];
	wire [0:0] recv_adp__recv__rdy [0:4];
	wire [0:0] recv_adp__recv__val [0:4];
	wire [0:0] recv_adp__send__en [0:4];
	wire [207:0] recv_adp__send__msg [0:4];
	wire [1:0] recv_adp__send__yum [0:4];
	RecvRTL2CreditSendRTL__1c17f17a9a80ace5 recv_adp__0(
		.clk(recv_adp__clk[0]),
		.reset(recv_adp__reset[0]),
		.recv__msg(recv_adp__recv__msg[0]),
		.recv__rdy(recv_adp__recv__rdy[0]),
		.recv__val(recv_adp__recv__val[0]),
		.send__en(recv_adp__send__en[0]),
		.send__msg(recv_adp__send__msg[0]),
		.send__yum(recv_adp__send__yum[0])
	);
	RecvRTL2CreditSendRTL__1c17f17a9a80ace5 recv_adp__1(
		.clk(recv_adp__clk[1]),
		.reset(recv_adp__reset[1]),
		.recv__msg(recv_adp__recv__msg[1]),
		.recv__rdy(recv_adp__recv__rdy[1]),
		.recv__val(recv_adp__recv__val[1]),
		.send__en(recv_adp__send__en[1]),
		.send__msg(recv_adp__send__msg[1]),
		.send__yum(recv_adp__send__yum[1])
	);
	RecvRTL2CreditSendRTL__1c17f17a9a80ace5 recv_adp__2(
		.clk(recv_adp__clk[2]),
		.reset(recv_adp__reset[2]),
		.recv__msg(recv_adp__recv__msg[2]),
		.recv__rdy(recv_adp__recv__rdy[2]),
		.recv__val(recv_adp__recv__val[2]),
		.send__en(recv_adp__send__en[2]),
		.send__msg(recv_adp__send__msg[2]),
		.send__yum(recv_adp__send__yum[2])
	);
	RecvRTL2CreditSendRTL__1c17f17a9a80ace5 recv_adp__3(
		.clk(recv_adp__clk[3]),
		.reset(recv_adp__reset[3]),
		.recv__msg(recv_adp__recv__msg[3]),
		.recv__rdy(recv_adp__recv__rdy[3]),
		.recv__val(recv_adp__recv__val[3]),
		.send__en(recv_adp__send__en[3]),
		.send__msg(recv_adp__send__msg[3]),
		.send__yum(recv_adp__send__yum[3])
	);
	RecvRTL2CreditSendRTL__1c17f17a9a80ace5 recv_adp__4(
		.clk(recv_adp__clk[4]),
		.reset(recv_adp__reset[4]),
		.recv__msg(recv_adp__recv__msg[4]),
		.recv__rdy(recv_adp__recv__rdy[4]),
		.recv__val(recv_adp__recv__val[4]),
		.send__en(recv_adp__send__en[4]),
		.send__msg(recv_adp__send__msg[4]),
		.send__yum(recv_adp__send__yum[4])
	);
	wire [0:0] routers__clk [0:4];
	reg [2:0] routers__pos [0:4];
	wire [0:0] routers__reset [0:4];
	wire [2:0] routers__recv__en [0:4];
	wire [623:0] routers__recv__msg [0:4];
	wire [5:0] routers__recv__yum [0:4];
	wire [2:0] routers__send__en [0:4];
	wire [623:0] routers__send__msg [0:4];
	wire [5:0] routers__send__yum [0:4];
	RingRouterRTL__aa12cf7d74338aa0 routers__0(
		.clk(routers__clk[0]),
		.pos(routers__pos[0]),
		.reset(routers__reset[0]),
		.recv__en(routers__recv__en[0]),
		.recv__msg(routers__recv__msg[0]),
		.recv__yum(routers__recv__yum[0]),
		.send__en(routers__send__en[0]),
		.send__msg(routers__send__msg[0]),
		.send__yum(routers__send__yum[0])
	);
	RingRouterRTL__aa12cf7d74338aa0 routers__1(
		.clk(routers__clk[1]),
		.pos(routers__pos[1]),
		.reset(routers__reset[1]),
		.recv__en(routers__recv__en[1]),
		.recv__msg(routers__recv__msg[1]),
		.recv__yum(routers__recv__yum[1]),
		.send__en(routers__send__en[1]),
		.send__msg(routers__send__msg[1]),
		.send__yum(routers__send__yum[1])
	);
	RingRouterRTL__aa12cf7d74338aa0 routers__2(
		.clk(routers__clk[2]),
		.pos(routers__pos[2]),
		.reset(routers__reset[2]),
		.recv__en(routers__recv__en[2]),
		.recv__msg(routers__recv__msg[2]),
		.recv__yum(routers__recv__yum[2]),
		.send__en(routers__send__en[2]),
		.send__msg(routers__send__msg[2]),
		.send__yum(routers__send__yum[2])
	);
	RingRouterRTL__aa12cf7d74338aa0 routers__3(
		.clk(routers__clk[3]),
		.pos(routers__pos[3]),
		.reset(routers__reset[3]),
		.recv__en(routers__recv__en[3]),
		.recv__msg(routers__recv__msg[3]),
		.recv__yum(routers__recv__yum[3]),
		.send__en(routers__send__en[3]),
		.send__msg(routers__send__msg[3]),
		.send__yum(routers__send__yum[3])
	);
	RingRouterRTL__aa12cf7d74338aa0 routers__4(
		.clk(routers__clk[4]),
		.pos(routers__pos[4]),
		.reset(routers__reset[4]),
		.recv__en(routers__recv__en[4]),
		.recv__msg(routers__recv__msg[4]),
		.recv__yum(routers__recv__yum[4]),
		.send__en(routers__send__en[4]),
		.send__msg(routers__send__msg[4]),
		.send__yum(routers__send__yum[4])
	);
	wire [0:0] send_adp__clk [0:4];
	wire [0:0] send_adp__reset [0:4];
	wire [0:0] send_adp__recv__en [0:4];
	wire [207:0] send_adp__recv__msg [0:4];
	wire [1:0] send_adp__recv__yum [0:4];
	wire [207:0] send_adp__send__msg [0:4];
	wire [0:0] send_adp__send__rdy [0:4];
	wire [0:0] send_adp__send__val [0:4];
	CreditRecvRTL2SendRTL__04ae6f3fc3c0287a send_adp__0(
		.clk(send_adp__clk[0]),
		.reset(send_adp__reset[0]),
		.recv__en(send_adp__recv__en[0]),
		.recv__msg(send_adp__recv__msg[0]),
		.recv__yum(send_adp__recv__yum[0]),
		.send__msg(send_adp__send__msg[0]),
		.send__rdy(send_adp__send__rdy[0]),
		.send__val(send_adp__send__val[0])
	);
	CreditRecvRTL2SendRTL__04ae6f3fc3c0287a send_adp__1(
		.clk(send_adp__clk[1]),
		.reset(send_adp__reset[1]),
		.recv__en(send_adp__recv__en[1]),
		.recv__msg(send_adp__recv__msg[1]),
		.recv__yum(send_adp__recv__yum[1]),
		.send__msg(send_adp__send__msg[1]),
		.send__rdy(send_adp__send__rdy[1]),
		.send__val(send_adp__send__val[1])
	);
	CreditRecvRTL2SendRTL__04ae6f3fc3c0287a send_adp__2(
		.clk(send_adp__clk[2]),
		.reset(send_adp__reset[2]),
		.recv__en(send_adp__recv__en[2]),
		.recv__msg(send_adp__recv__msg[2]),
		.recv__yum(send_adp__recv__yum[2]),
		.send__msg(send_adp__send__msg[2]),
		.send__rdy(send_adp__send__rdy[2]),
		.send__val(send_adp__send__val[2])
	);
	CreditRecvRTL2SendRTL__04ae6f3fc3c0287a send_adp__3(
		.clk(send_adp__clk[3]),
		.reset(send_adp__reset[3]),
		.recv__en(send_adp__recv__en[3]),
		.recv__msg(send_adp__recv__msg[3]),
		.recv__yum(send_adp__recv__yum[3]),
		.send__msg(send_adp__send__msg[3]),
		.send__rdy(send_adp__send__rdy[3]),
		.send__val(send_adp__send__val[3])
	);
	CreditRecvRTL2SendRTL__04ae6f3fc3c0287a send_adp__4(
		.clk(send_adp__clk[4]),
		.reset(send_adp__reset[4]),
		.recv__en(send_adp__recv__en[4]),
		.recv__msg(send_adp__recv__msg[4]),
		.recv__yum(send_adp__recv__yum[4]),
		.send__msg(send_adp__send__msg[4]),
		.send__rdy(send_adp__send__rdy[4]),
		.send__val(send_adp__send__val[4])
	);
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : up_pos
		begin : sv2v_autoblock_1
			reg [31:0] r;
			for (r = 1'd0; r < 3'd5; r = r + 1'd1)
				routers__pos[sv2v_cast_3(r)] = sv2v_cast_3(r);
		end
	end
	assign routers__clk[0] = clk;
	assign routers__reset[0] = reset;
	assign routers__clk[1] = clk;
	assign routers__reset[1] = reset;
	assign routers__clk[2] = clk;
	assign routers__reset[2] = reset;
	assign routers__clk[3] = clk;
	assign routers__reset[3] = reset;
	assign routers__clk[4] = clk;
	assign routers__reset[4] = reset;
	assign recv_adp__clk[0] = clk;
	assign recv_adp__reset[0] = reset;
	assign recv_adp__clk[1] = clk;
	assign recv_adp__reset[1] = reset;
	assign recv_adp__clk[2] = clk;
	assign recv_adp__reset[2] = reset;
	assign recv_adp__clk[3] = clk;
	assign recv_adp__reset[3] = reset;
	assign recv_adp__clk[4] = clk;
	assign recv_adp__reset[4] = reset;
	assign send_adp__clk[0] = clk;
	assign send_adp__reset[0] = reset;
	assign send_adp__clk[1] = clk;
	assign send_adp__reset[1] = reset;
	assign send_adp__clk[2] = clk;
	assign send_adp__reset[2] = reset;
	assign send_adp__clk[3] = clk;
	assign send_adp__reset[3] = reset;
	assign send_adp__clk[4] = clk;
	assign send_adp__reset[4] = reset;
	assign routers__recv__en[1][2+:1] = routers__send__en[0][1+:1];
	assign routers__recv__msg[1][416+:208] = routers__send__msg[0][208+:208];
	assign routers__send__yum[0][3+:1] = routers__recv__yum[1][5+:1];
	assign routers__send__yum[0][2+:1] = routers__recv__yum[1][4+:1];
	assign routers__recv__en[0][1+:1] = routers__send__en[1][2+:1];
	assign routers__recv__msg[0][208+:208] = routers__send__msg[1][416+:208];
	assign routers__send__yum[1][5+:1] = routers__recv__yum[0][3+:1];
	assign routers__send__yum[1][4+:1] = routers__recv__yum[0][2+:1];
	assign recv_adp__recv__msg[0] = recv__msg[832+:208];
	assign recv__rdy[4+:1] = recv_adp__recv__rdy[0];
	assign recv_adp__recv__val[0] = recv__val[4+:1];
	assign routers__recv__en[0][0+:1] = recv_adp__send__en[0];
	assign routers__recv__msg[0][0+:208] = recv_adp__send__msg[0];
	assign recv_adp__send__yum[0][1+:1] = routers__recv__yum[0][1+:1];
	assign recv_adp__send__yum[0][0+:1] = routers__recv__yum[0][0+:1];
	assign send_adp__recv__en[0] = routers__send__en[0][0+:1];
	assign send_adp__recv__msg[0] = routers__send__msg[0][0+:208];
	assign routers__send__yum[0][1+:1] = send_adp__recv__yum[0][1+:1];
	assign routers__send__yum[0][0+:1] = send_adp__recv__yum[0][0+:1];
	assign send__msg[832+:208] = send_adp__send__msg[0];
	assign send_adp__send__rdy[0] = send__rdy[4+:1];
	assign send__val[4+:1] = send_adp__send__val[0];
	assign routers__recv__en[2][2+:1] = routers__send__en[1][1+:1];
	assign routers__recv__msg[2][416+:208] = routers__send__msg[1][208+:208];
	assign routers__send__yum[1][3+:1] = routers__recv__yum[2][5+:1];
	assign routers__send__yum[1][2+:1] = routers__recv__yum[2][4+:1];
	assign routers__recv__en[1][1+:1] = routers__send__en[2][2+:1];
	assign routers__recv__msg[1][208+:208] = routers__send__msg[2][416+:208];
	assign routers__send__yum[2][5+:1] = routers__recv__yum[1][3+:1];
	assign routers__send__yum[2][4+:1] = routers__recv__yum[1][2+:1];
	assign recv_adp__recv__msg[1] = recv__msg[624+:208];
	assign recv__rdy[3+:1] = recv_adp__recv__rdy[1];
	assign recv_adp__recv__val[1] = recv__val[3+:1];
	assign routers__recv__en[1][0+:1] = recv_adp__send__en[1];
	assign routers__recv__msg[1][0+:208] = recv_adp__send__msg[1];
	assign recv_adp__send__yum[1][1+:1] = routers__recv__yum[1][1+:1];
	assign recv_adp__send__yum[1][0+:1] = routers__recv__yum[1][0+:1];
	assign send_adp__recv__en[1] = routers__send__en[1][0+:1];
	assign send_adp__recv__msg[1] = routers__send__msg[1][0+:208];
	assign routers__send__yum[1][1+:1] = send_adp__recv__yum[1][1+:1];
	assign routers__send__yum[1][0+:1] = send_adp__recv__yum[1][0+:1];
	assign send__msg[624+:208] = send_adp__send__msg[1];
	assign send_adp__send__rdy[1] = send__rdy[3+:1];
	assign send__val[3+:1] = send_adp__send__val[1];
	assign routers__recv__en[3][2+:1] = routers__send__en[2][1+:1];
	assign routers__recv__msg[3][416+:208] = routers__send__msg[2][208+:208];
	assign routers__send__yum[2][3+:1] = routers__recv__yum[3][5+:1];
	assign routers__send__yum[2][2+:1] = routers__recv__yum[3][4+:1];
	assign routers__recv__en[2][1+:1] = routers__send__en[3][2+:1];
	assign routers__recv__msg[2][208+:208] = routers__send__msg[3][416+:208];
	assign routers__send__yum[3][5+:1] = routers__recv__yum[2][3+:1];
	assign routers__send__yum[3][4+:1] = routers__recv__yum[2][2+:1];
	assign recv_adp__recv__msg[2] = recv__msg[416+:208];
	assign recv__rdy[2+:1] = recv_adp__recv__rdy[2];
	assign recv_adp__recv__val[2] = recv__val[2+:1];
	assign routers__recv__en[2][0+:1] = recv_adp__send__en[2];
	assign routers__recv__msg[2][0+:208] = recv_adp__send__msg[2];
	assign recv_adp__send__yum[2][1+:1] = routers__recv__yum[2][1+:1];
	assign recv_adp__send__yum[2][0+:1] = routers__recv__yum[2][0+:1];
	assign send_adp__recv__en[2] = routers__send__en[2][0+:1];
	assign send_adp__recv__msg[2] = routers__send__msg[2][0+:208];
	assign routers__send__yum[2][1+:1] = send_adp__recv__yum[2][1+:1];
	assign routers__send__yum[2][0+:1] = send_adp__recv__yum[2][0+:1];
	assign send__msg[416+:208] = send_adp__send__msg[2];
	assign send_adp__send__rdy[2] = send__rdy[2+:1];
	assign send__val[2+:1] = send_adp__send__val[2];
	assign routers__recv__en[4][2+:1] = routers__send__en[3][1+:1];
	assign routers__recv__msg[4][416+:208] = routers__send__msg[3][208+:208];
	assign routers__send__yum[3][3+:1] = routers__recv__yum[4][5+:1];
	assign routers__send__yum[3][2+:1] = routers__recv__yum[4][4+:1];
	assign routers__recv__en[3][1+:1] = routers__send__en[4][2+:1];
	assign routers__recv__msg[3][208+:208] = routers__send__msg[4][416+:208];
	assign routers__send__yum[4][5+:1] = routers__recv__yum[3][3+:1];
	assign routers__send__yum[4][4+:1] = routers__recv__yum[3][2+:1];
	assign recv_adp__recv__msg[3] = recv__msg[208+:208];
	assign recv__rdy[1+:1] = recv_adp__recv__rdy[3];
	assign recv_adp__recv__val[3] = recv__val[1+:1];
	assign routers__recv__en[3][0+:1] = recv_adp__send__en[3];
	assign routers__recv__msg[3][0+:208] = recv_adp__send__msg[3];
	assign recv_adp__send__yum[3][1+:1] = routers__recv__yum[3][1+:1];
	assign recv_adp__send__yum[3][0+:1] = routers__recv__yum[3][0+:1];
	assign send_adp__recv__en[3] = routers__send__en[3][0+:1];
	assign send_adp__recv__msg[3] = routers__send__msg[3][0+:208];
	assign routers__send__yum[3][1+:1] = send_adp__recv__yum[3][1+:1];
	assign routers__send__yum[3][0+:1] = send_adp__recv__yum[3][0+:1];
	assign send__msg[208+:208] = send_adp__send__msg[3];
	assign send_adp__send__rdy[3] = send__rdy[1+:1];
	assign send__val[1+:1] = send_adp__send__val[3];
	assign routers__recv__en[0][2+:1] = routers__send__en[4][1+:1];
	assign routers__recv__msg[0][416+:208] = routers__send__msg[4][208+:208];
	assign routers__send__yum[4][3+:1] = routers__recv__yum[0][5+:1];
	assign routers__send__yum[4][2+:1] = routers__recv__yum[0][4+:1];
	assign routers__recv__en[4][1+:1] = routers__send__en[0][2+:1];
	assign routers__recv__msg[4][208+:208] = routers__send__msg[0][416+:208];
	assign routers__send__yum[0][5+:1] = routers__recv__yum[4][3+:1];
	assign routers__send__yum[0][4+:1] = routers__recv__yum[4][2+:1];
	assign recv_adp__recv__msg[4] = recv__msg[0+:208];
	assign recv__rdy[0+:1] = recv_adp__recv__rdy[4];
	assign recv_adp__recv__val[4] = recv__val[0+:1];
	assign routers__recv__en[4][0+:1] = recv_adp__send__en[4];
	assign routers__recv__msg[4][0+:208] = recv_adp__send__msg[4];
	assign recv_adp__send__yum[4][1+:1] = routers__recv__yum[4][1+:1];
	assign recv_adp__send__yum[4][0+:1] = routers__recv__yum[4][0+:1];
	assign send_adp__recv__en[4] = routers__send__en[4][0+:1];
	assign send_adp__recv__msg[4] = routers__send__msg[4][0+:208];
	assign routers__send__yum[4][1+:1] = send_adp__recv__yum[4][1+:1];
	assign routers__send__yum[4][0+:1] = send_adp__recv__yum[4][0+:1];
	assign send__msg[0+:208] = send_adp__send__msg[4];
	assign send_adp__send__rdy[4] = send__rdy[0+:1];
	assign send__val[0+:1] = send_adp__send__val[4];
endmodule
module Mux__Type_TileSramXbarPacket_3_3_8__def7c15279e62b76__ninputs_2 (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [23:0] in_;
	output reg [11:0] out;
	input wire [0:0] reset;
	input wire [0:0] sel;
	always @(*) begin : up_mux
		out = in_[(1 - sel) * 12+:12];
	end
endmodule
module RegisterFile__d11da69b87f553e2 (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	output reg [11:0] rdata;
	input wire [0:0] reset;
	input wire [0:0] waddr;
	input wire [11:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [11:0] regs [0:1];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 12+:12] = regs[raddr[sv2v_cast_1(i)+:1]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i)+:1]] <= wdata[sv2v_cast_1(i) * 12+:12];
		end
	end
endmodule
module BypassQueueDpathRTL__02bcfd8a5abd190f (
	clk,
	mux_sel,
	raddr,
	recv_msg,
	reset,
	send_msg,
	waddr,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] mux_sel;
	input wire [0:0] raddr;
	input wire [11:0] recv_msg;
	input wire [0:0] reset;
	output wire [11:0] send_msg;
	input wire [0:0] waddr;
	input wire [0:0] wen;
	wire [0:0] mux__clk;
	wire [23:0] mux__in_;
	wire [11:0] mux__out;
	wire [0:0] mux__reset;
	wire [0:0] mux__sel;
	Mux__Type_TileSramXbarPacket_3_3_8__def7c15279e62b76__ninputs_2 mux(
		.clk(mux__clk),
		.in_(mux__in_),
		.out(mux__out),
		.reset(mux__reset),
		.sel(mux__sel)
	);
	wire [0:0] rf__clk;
	wire [0:0] rf__raddr;
	wire [11:0] rf__rdata;
	wire [0:0] rf__reset;
	wire [0:0] rf__waddr;
	wire [11:0] rf__wdata;
	wire [0:0] rf__wen;
	RegisterFile__d11da69b87f553e2 rf(
		.clk(rf__clk),
		.raddr(rf__raddr),
		.rdata(rf__rdata),
		.reset(rf__reset),
		.waddr(rf__waddr),
		.wdata(rf__wdata),
		.wen(rf__wen)
	);
	assign rf__clk = clk;
	assign rf__reset = reset;
	assign rf__raddr[0+:1] = raddr;
	assign rf__wen[0+:1] = wen;
	assign rf__waddr[0+:1] = waddr;
	assign rf__wdata[0+:12] = recv_msg;
	assign mux__clk = clk;
	assign mux__reset = reset;
	assign mux__sel = mux_sel;
	assign mux__in_[12+:12] = rf__rdata[0+:12];
	assign mux__in_[0+:12] = recv_msg;
	assign send_msg = mux__out;
endmodule
module BypassQueueRTL__02bcfd8a5abd190f (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1:0] count;
	input wire [0:0] reset;
	input wire [11:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [11:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] ctrl__clk;
	wire [1:0] ctrl__count;
	wire [0:0] ctrl__mux_sel;
	wire [0:0] ctrl__raddr;
	wire [0:0] ctrl__recv_rdy;
	wire [0:0] ctrl__recv_val;
	wire [0:0] ctrl__reset;
	wire [0:0] ctrl__send_rdy;
	wire [0:0] ctrl__send_val;
	wire [0:0] ctrl__waddr;
	wire [0:0] ctrl__wen;
	BypassQueueCtrlRTL__num_entries_2 ctrl(
		.clk(ctrl__clk),
		.count(ctrl__count),
		.mux_sel(ctrl__mux_sel),
		.raddr(ctrl__raddr),
		.recv_rdy(ctrl__recv_rdy),
		.recv_val(ctrl__recv_val),
		.reset(ctrl__reset),
		.send_rdy(ctrl__send_rdy),
		.send_val(ctrl__send_val),
		.waddr(ctrl__waddr),
		.wen(ctrl__wen)
	);
	wire [0:0] dpath__clk;
	wire [0:0] dpath__mux_sel;
	wire [0:0] dpath__raddr;
	wire [11:0] dpath__recv_msg;
	wire [0:0] dpath__reset;
	wire [11:0] dpath__send_msg;
	wire [0:0] dpath__waddr;
	wire [0:0] dpath__wen;
	BypassQueueDpathRTL__02bcfd8a5abd190f dpath(
		.clk(dpath__clk),
		.mux_sel(dpath__mux_sel),
		.raddr(dpath__raddr),
		.recv_msg(dpath__recv_msg),
		.reset(dpath__reset),
		.send_msg(dpath__send_msg),
		.waddr(dpath__waddr),
		.wen(dpath__wen)
	);
	assign ctrl__clk = clk;
	assign ctrl__reset = reset;
	assign dpath__clk = clk;
	assign dpath__reset = reset;
	assign dpath__wen = ctrl__wen;
	assign dpath__waddr = ctrl__waddr;
	assign dpath__raddr = ctrl__raddr;
	assign dpath__mux_sel = ctrl__mux_sel;
	assign ctrl__recv_val = recv__val;
	assign recv__rdy = ctrl__recv_rdy;
	assign send__val = ctrl__send_val;
	assign ctrl__send_rdy = send__rdy;
	assign count = ctrl__count;
	assign dpath__recv_msg = recv__msg;
	assign send__msg = dpath__send_msg;
endmodule
module InputUnitRTL__776c3eb5e5cfc2f2 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [11:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [11:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] queue__clk;
	wire [1:0] queue__count;
	wire [0:0] queue__reset;
	wire [11:0] queue__recv__msg;
	wire [0:0] queue__recv__rdy;
	wire [0:0] queue__recv__val;
	wire [11:0] queue__send__msg;
	wire [0:0] queue__send__rdy;
	wire [0:0] queue__send__val;
	BypassQueueRTL__02bcfd8a5abd190f queue(
		.clk(queue__clk),
		.count(queue__count),
		.reset(queue__reset),
		.recv__msg(queue__recv__msg),
		.recv__rdy(queue__recv__rdy),
		.recv__val(queue__recv__val),
		.send__msg(queue__send__msg),
		.send__rdy(queue__send__rdy),
		.send__val(queue__send__val)
	);
	assign queue__clk = clk;
	assign queue__reset = reset;
	assign queue__recv__msg = recv__msg;
	assign recv__rdy = queue__recv__rdy;
	assign queue__recv__val = recv__val;
	assign send__msg = queue__send__msg;
	assign queue__send__rdy = send__rdy;
	assign send__val = queue__send__val;
endmodule
module OutputUnitRTL__d3d30ad34100962c (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [11:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [11:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	assign send__msg = recv__msg;
	assign recv__rdy = send__rdy;
	assign send__val = recv__val;
endmodule
module XbarRouteUnitRTL__f75311e3596366b0 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [11:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [35:0] send__msg;
	input wire [2:0] send__rdy;
	output reg [2:0] send__val;
	localparam [1:0] __const__num_outports_at_up_ru_routing = 2'd3;
	reg [1:0] out_dir;
	wire [2:0] send_val;
	always @(*) begin : up_ru_recv_rdy
		recv__rdy = send__rdy[2 - out_dir+:1] > 1'd0;
	end
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : up_ru_routing
		out_dir = recv__msg[9-:2];
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_up_ru_routing; i = i + 1'd1)
				send__val[2 - sv2v_cast_2(i)+:1] = 1'd0;
		end
		if (recv__val)
			send__val[2 - out_dir+:1] = 1'd1;
	end
	assign send__msg[24+:12] = recv__msg;
	assign send_val[0:0] = send__val[2+:1];
	assign send__msg[12+:12] = recv__msg;
	assign send_val[1:1] = send__val[1+:1];
	assign send__msg[0+:12] = recv__msg;
	assign send_val[2:2] = send__val[0+:1];
endmodule
module RegEnRst__Type_Bits3__reset_value_1 (
	clk,
	en,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	input wire [2:0] in_;
	output reg [2:0] out;
	input wire [0:0] reset;
	localparam [0:0] __const__reset_value_at_up_regenrst = 1'd1;
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(posedge clk) begin : up_regenrst
		if (reset)
			out <= sv2v_cast_3(__const__reset_value_at_up_regenrst);
		else if (en)
			out <= in_;
	end
endmodule
module RoundRobinArbiterEn__nreqs_3 (
	clk,
	en,
	grants,
	reqs,
	reset
);
	input wire [0:0] clk;
	input wire [0:0] en;
	output reg [2:0] grants;
	input wire [2:0] reqs;
	input wire [0:0] reset;
	localparam [1:0] __const__nreqs_at_comb_reqs_int = 2'd3;
	localparam [2:0] __const__nreqsX2_at_comb_reqs_int = 3'd6;
	localparam [1:0] __const__nreqs_at_comb_grants = 2'd3;
	localparam [1:0] __const__nreqs_at_comb_priority_int = 2'd3;
	localparam [2:0] __const__nreqsX2_at_comb_priority_int = 3'd6;
	localparam [2:0] __const__nreqsX2_at_comb_kills = 3'd6;
	localparam [2:0] __const__nreqsX2_at_comb_grants_int = 3'd6;
	reg [5:0] grants_int;
	reg [6:0] kills;
	reg [0:0] priority_en;
	reg [5:0] priority_int;
	reg [5:0] reqs_int;
	wire [0:0] priority_reg__clk;
	wire [0:0] priority_reg__en;
	wire [2:0] priority_reg__in_;
	wire [2:0] priority_reg__out;
	wire [0:0] priority_reg__reset;
	RegEnRst__Type_Bits3__reset_value_1 priority_reg(
		.clk(priority_reg__clk),
		.en(priority_reg__en),
		.in_(priority_reg__in_),
		.out(priority_reg__out),
		.reset(priority_reg__reset)
	);
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : comb_grants
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqs_at_comb_grants; i = i + 1'd1)
				grants[sv2v_cast_2(i)] = grants_int[sv2v_cast_3(i)] | grants_int[sv2v_cast_3(__const__nreqs_at_comb_grants) + sv2v_cast_3(i)];
		end
	end
	always @(*) begin : comb_grants_int
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_grants_int; i = i + 1'd1)
				if (priority_int[sv2v_cast_3(i)])
					grants_int[sv2v_cast_3(i)] = reqs_int[sv2v_cast_3(i)];
				else
					grants_int[sv2v_cast_3(i)] = ~kills[sv2v_cast_3(i)] & reqs_int[sv2v_cast_3(i)];
		end
	end
	always @(*) begin : comb_kills
		kills[3'd0] = 1'd1;
		begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__nreqsX2_at_comb_kills; i = i + 1'd1)
				if (priority_int[sv2v_cast_3(i)])
					kills[sv2v_cast_3(i) + 3'd1] = reqs_int[sv2v_cast_3(i)];
				else
					kills[sv2v_cast_3(i) + 3'd1] = kills[sv2v_cast_3(i)] | (~kills[sv2v_cast_3(i)] & reqs_int[sv2v_cast_3(i)]);
		end
	end
	always @(*) begin : comb_priority_en
		priority_en = (grants != 3'd0) & en;
	end
	always @(*) begin : comb_priority_int
		priority_int[3'd2:3'd0] = priority_reg__out;
		priority_int[3'd5:sv2v_cast_3(__const__nreqs_at_comb_priority_int)] = 3'd0;
	end
	always @(*) begin : comb_reqs_int
		reqs_int[3'd2:3'd0] = reqs;
		reqs_int[3'd5:sv2v_cast_3(__const__nreqs_at_comb_reqs_int)] = reqs;
	end
	assign priority_reg__clk = clk;
	assign priority_reg__reset = reset;
	assign priority_reg__en = priority_en;
	assign priority_reg__in_[2:1] = grants[1:0];
	assign priority_reg__in_[0:0] = grants[2:2];
endmodule
module Encoder__in_nbits_3__out_nbits_2 (
	clk,
	in_,
	out,
	reset
);
	input wire [0:0] clk;
	input wire [2:0] in_;
	output reg [1:0] out;
	input wire [0:0] reset;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : encode
		out = 2'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < 2'd3; i = i + 1'd1)
				if (in_[sv2v_cast_2(i)])
					out = sv2v_cast_2(i);
		end
	end
endmodule
module Mux__Type_TileSramXbarPacket_3_3_8__def7c15279e62b76__ninputs_3 (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [35:0] in_;
	output reg [11:0] out;
	input wire [0:0] reset;
	input wire [1:0] sel;
	always @(*) begin : up_mux
		out = in_[(2 - sel) * 12+:12];
	end
endmodule
module SwitchUnitRTL__b843f64e453529e4 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [35:0] recv__msg;
	output reg [2:0] recv__rdy;
	input wire [2:0] recv__val;
	output wire [11:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	localparam [1:0] __const__num_inports_at_up_get_en = 2'd3;
	wire [0:0] arbiter__clk;
	wire [0:0] arbiter__en;
	wire [2:0] arbiter__grants;
	wire [2:0] arbiter__reqs;
	wire [0:0] arbiter__reset;
	RoundRobinArbiterEn__nreqs_3 arbiter(
		.clk(arbiter__clk),
		.en(arbiter__en),
		.grants(arbiter__grants),
		.reqs(arbiter__reqs),
		.reset(arbiter__reset)
	);
	wire [0:0] encoder__clk;
	wire [2:0] encoder__in_;
	wire [1:0] encoder__out;
	wire [0:0] encoder__reset;
	Encoder__in_nbits_3__out_nbits_2 encoder(
		.clk(encoder__clk),
		.in_(encoder__in_),
		.out(encoder__out),
		.reset(encoder__reset)
	);
	wire [0:0] mux__clk;
	wire [35:0] mux__in_;
	wire [11:0] mux__out;
	wire [0:0] mux__reset;
	wire [1:0] mux__sel;
	Mux__Type_TileSramXbarPacket_3_3_8__def7c15279e62b76__ninputs_3 mux(
		.clk(mux__clk),
		.in_(mux__in_),
		.out(mux__out),
		.reset(mux__reset),
		.sel(mux__sel)
	);
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : up_get_en
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_up_get_en; i = i + 1'd1)
				recv__rdy[2 - sv2v_cast_2(i)+:1] = send__rdy & (mux__sel == sv2v_cast_2(i));
		end
	end
	always @(*) begin : up_send_val
		send__val = arbiter__grants > 3'd0;
	end
	assign arbiter__clk = clk;
	assign arbiter__reset = reset;
	assign arbiter__en = 1'd1;
	assign mux__clk = clk;
	assign mux__reset = reset;
	assign send__msg = mux__out;
	assign encoder__clk = clk;
	assign encoder__reset = reset;
	assign encoder__in_ = arbiter__grants;
	assign mux__sel = encoder__out;
	assign arbiter__reqs[0:0] = recv__val[2+:1];
	assign mux__in_[24+:12] = recv__msg[24+:12];
	assign arbiter__reqs[1:1] = recv__val[1+:1];
	assign mux__in_[12+:12] = recv__msg[12+:12];
	assign arbiter__reqs[2:2] = recv__val[0+:1];
	assign mux__in_[0+:12] = recv__msg[0+:12];
endmodule
module XbarBypassQueueRTL__479e104af07e8511 (
	clk,
	packet_on_input_units,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [35:0] packet_on_input_units;
	input wire [0:0] reset;
	input wire [35:0] recv__msg;
	output wire [2:0] recv__rdy;
	input wire [2:0] recv__val;
	output wire [35:0] send__msg;
	input wire [2:0] send__rdy;
	output wire [2:0] send__val;
	wire [0:0] input_units__clk [0:2];
	wire [0:0] input_units__reset [0:2];
	wire [11:0] input_units__recv__msg [0:2];
	wire [0:0] input_units__recv__rdy [0:2];
	wire [0:0] input_units__recv__val [0:2];
	wire [11:0] input_units__send__msg [0:2];
	wire [0:0] input_units__send__rdy [0:2];
	wire [0:0] input_units__send__val [0:2];
	InputUnitRTL__776c3eb5e5cfc2f2 input_units__0(
		.clk(input_units__clk[0]),
		.reset(input_units__reset[0]),
		.recv__msg(input_units__recv__msg[0]),
		.recv__rdy(input_units__recv__rdy[0]),
		.recv__val(input_units__recv__val[0]),
		.send__msg(input_units__send__msg[0]),
		.send__rdy(input_units__send__rdy[0]),
		.send__val(input_units__send__val[0])
	);
	InputUnitRTL__776c3eb5e5cfc2f2 input_units__1(
		.clk(input_units__clk[1]),
		.reset(input_units__reset[1]),
		.recv__msg(input_units__recv__msg[1]),
		.recv__rdy(input_units__recv__rdy[1]),
		.recv__val(input_units__recv__val[1]),
		.send__msg(input_units__send__msg[1]),
		.send__rdy(input_units__send__rdy[1]),
		.send__val(input_units__send__val[1])
	);
	InputUnitRTL__776c3eb5e5cfc2f2 input_units__2(
		.clk(input_units__clk[2]),
		.reset(input_units__reset[2]),
		.recv__msg(input_units__recv__msg[2]),
		.recv__rdy(input_units__recv__rdy[2]),
		.recv__val(input_units__recv__val[2]),
		.send__msg(input_units__send__msg[2]),
		.send__rdy(input_units__send__rdy[2]),
		.send__val(input_units__send__val[2])
	);
	wire [0:0] output_units__clk [0:2];
	wire [0:0] output_units__reset [0:2];
	wire [11:0] output_units__recv__msg [0:2];
	wire [0:0] output_units__recv__rdy [0:2];
	wire [0:0] output_units__recv__val [0:2];
	wire [11:0] output_units__send__msg [0:2];
	wire [0:0] output_units__send__rdy [0:2];
	wire [0:0] output_units__send__val [0:2];
	OutputUnitRTL__d3d30ad34100962c output_units__0(
		.clk(output_units__clk[0]),
		.reset(output_units__reset[0]),
		.recv__msg(output_units__recv__msg[0]),
		.recv__rdy(output_units__recv__rdy[0]),
		.recv__val(output_units__recv__val[0]),
		.send__msg(output_units__send__msg[0]),
		.send__rdy(output_units__send__rdy[0]),
		.send__val(output_units__send__val[0])
	);
	OutputUnitRTL__d3d30ad34100962c output_units__1(
		.clk(output_units__clk[1]),
		.reset(output_units__reset[1]),
		.recv__msg(output_units__recv__msg[1]),
		.recv__rdy(output_units__recv__rdy[1]),
		.recv__val(output_units__recv__val[1]),
		.send__msg(output_units__send__msg[1]),
		.send__rdy(output_units__send__rdy[1]),
		.send__val(output_units__send__val[1])
	);
	OutputUnitRTL__d3d30ad34100962c output_units__2(
		.clk(output_units__clk[2]),
		.reset(output_units__reset[2]),
		.recv__msg(output_units__recv__msg[2]),
		.recv__rdy(output_units__recv__rdy[2]),
		.recv__val(output_units__recv__val[2]),
		.send__msg(output_units__send__msg[2]),
		.send__rdy(output_units__send__rdy[2]),
		.send__val(output_units__send__val[2])
	);
	wire [0:0] route_units__clk [0:2];
	wire [0:0] route_units__reset [0:2];
	wire [11:0] route_units__recv__msg [0:2];
	wire [0:0] route_units__recv__rdy [0:2];
	wire [0:0] route_units__recv__val [0:2];
	wire [35:0] route_units__send__msg [0:2];
	wire [2:0] route_units__send__rdy [0:2];
	wire [2:0] route_units__send__val [0:2];
	XbarRouteUnitRTL__f75311e3596366b0 route_units__0(
		.clk(route_units__clk[0]),
		.reset(route_units__reset[0]),
		.recv__msg(route_units__recv__msg[0]),
		.recv__rdy(route_units__recv__rdy[0]),
		.recv__val(route_units__recv__val[0]),
		.send__msg(route_units__send__msg[0]),
		.send__rdy(route_units__send__rdy[0]),
		.send__val(route_units__send__val[0])
	);
	XbarRouteUnitRTL__f75311e3596366b0 route_units__1(
		.clk(route_units__clk[1]),
		.reset(route_units__reset[1]),
		.recv__msg(route_units__recv__msg[1]),
		.recv__rdy(route_units__recv__rdy[1]),
		.recv__val(route_units__recv__val[1]),
		.send__msg(route_units__send__msg[1]),
		.send__rdy(route_units__send__rdy[1]),
		.send__val(route_units__send__val[1])
	);
	XbarRouteUnitRTL__f75311e3596366b0 route_units__2(
		.clk(route_units__clk[2]),
		.reset(route_units__reset[2]),
		.recv__msg(route_units__recv__msg[2]),
		.recv__rdy(route_units__recv__rdy[2]),
		.recv__val(route_units__recv__val[2]),
		.send__msg(route_units__send__msg[2]),
		.send__rdy(route_units__send__rdy[2]),
		.send__val(route_units__send__val[2])
	);
	wire [0:0] switch_units__clk [0:2];
	wire [0:0] switch_units__reset [0:2];
	wire [35:0] switch_units__recv__msg [0:2];
	wire [2:0] switch_units__recv__rdy [0:2];
	wire [2:0] switch_units__recv__val [0:2];
	wire [11:0] switch_units__send__msg [0:2];
	wire [0:0] switch_units__send__rdy [0:2];
	wire [0:0] switch_units__send__val [0:2];
	SwitchUnitRTL__b843f64e453529e4 switch_units__0(
		.clk(switch_units__clk[0]),
		.reset(switch_units__reset[0]),
		.recv__msg(switch_units__recv__msg[0]),
		.recv__rdy(switch_units__recv__rdy[0]),
		.recv__val(switch_units__recv__val[0]),
		.send__msg(switch_units__send__msg[0]),
		.send__rdy(switch_units__send__rdy[0]),
		.send__val(switch_units__send__val[0])
	);
	SwitchUnitRTL__b843f64e453529e4 switch_units__1(
		.clk(switch_units__clk[1]),
		.reset(switch_units__reset[1]),
		.recv__msg(switch_units__recv__msg[1]),
		.recv__rdy(switch_units__recv__rdy[1]),
		.recv__val(switch_units__recv__val[1]),
		.send__msg(switch_units__send__msg[1]),
		.send__rdy(switch_units__send__rdy[1]),
		.send__val(switch_units__send__val[1])
	);
	SwitchUnitRTL__b843f64e453529e4 switch_units__2(
		.clk(switch_units__clk[2]),
		.reset(switch_units__reset[2]),
		.recv__msg(switch_units__recv__msg[2]),
		.recv__rdy(switch_units__recv__rdy[2]),
		.recv__val(switch_units__recv__val[2]),
		.send__msg(switch_units__send__msg[2]),
		.send__rdy(switch_units__send__rdy[2]),
		.send__val(switch_units__send__val[2])
	);
	assign input_units__clk[0] = clk;
	assign input_units__reset[0] = reset;
	assign input_units__clk[1] = clk;
	assign input_units__reset[1] = reset;
	assign input_units__clk[2] = clk;
	assign input_units__reset[2] = reset;
	assign route_units__clk[0] = clk;
	assign route_units__reset[0] = reset;
	assign route_units__clk[1] = clk;
	assign route_units__reset[1] = reset;
	assign route_units__clk[2] = clk;
	assign route_units__reset[2] = reset;
	assign switch_units__clk[0] = clk;
	assign switch_units__reset[0] = reset;
	assign switch_units__clk[1] = clk;
	assign switch_units__reset[1] = reset;
	assign switch_units__clk[2] = clk;
	assign switch_units__reset[2] = reset;
	assign output_units__clk[0] = clk;
	assign output_units__reset[0] = reset;
	assign output_units__clk[1] = clk;
	assign output_units__reset[1] = reset;
	assign output_units__clk[2] = clk;
	assign output_units__reset[2] = reset;
	assign packet_on_input_units[24+:12] = input_units__send__msg[0];
	assign packet_on_input_units[12+:12] = input_units__send__msg[1];
	assign packet_on_input_units[0+:12] = input_units__send__msg[2];
	assign input_units__recv__msg[0] = recv__msg[24+:12];
	assign recv__rdy[2+:1] = input_units__recv__rdy[0];
	assign input_units__recv__val[0] = recv__val[2+:1];
	assign route_units__recv__msg[0] = input_units__send__msg[0];
	assign input_units__send__rdy[0] = route_units__recv__rdy[0];
	assign route_units__recv__val[0] = input_units__send__val[0];
	assign input_units__recv__msg[1] = recv__msg[12+:12];
	assign recv__rdy[1+:1] = input_units__recv__rdy[1];
	assign input_units__recv__val[1] = recv__val[1+:1];
	assign route_units__recv__msg[1] = input_units__send__msg[1];
	assign input_units__send__rdy[1] = route_units__recv__rdy[1];
	assign route_units__recv__val[1] = input_units__send__val[1];
	assign input_units__recv__msg[2] = recv__msg[0+:12];
	assign recv__rdy[0+:1] = input_units__recv__rdy[2];
	assign input_units__recv__val[2] = recv__val[0+:1];
	assign route_units__recv__msg[2] = input_units__send__msg[2];
	assign input_units__send__rdy[2] = route_units__recv__rdy[2];
	assign route_units__recv__val[2] = input_units__send__val[2];
	assign switch_units__recv__msg[0][24+:12] = route_units__send__msg[0][24+:12];
	assign route_units__send__rdy[0][2+:1] = switch_units__recv__rdy[0][2+:1];
	assign switch_units__recv__val[0][2+:1] = route_units__send__val[0][2+:1];
	assign switch_units__recv__msg[1][24+:12] = route_units__send__msg[0][12+:12];
	assign route_units__send__rdy[0][1+:1] = switch_units__recv__rdy[1][2+:1];
	assign switch_units__recv__val[1][2+:1] = route_units__send__val[0][1+:1];
	assign switch_units__recv__msg[2][24+:12] = route_units__send__msg[0][0+:12];
	assign route_units__send__rdy[0][0+:1] = switch_units__recv__rdy[2][2+:1];
	assign switch_units__recv__val[2][2+:1] = route_units__send__val[0][0+:1];
	assign switch_units__recv__msg[0][12+:12] = route_units__send__msg[1][24+:12];
	assign route_units__send__rdy[1][2+:1] = switch_units__recv__rdy[0][1+:1];
	assign switch_units__recv__val[0][1+:1] = route_units__send__val[1][2+:1];
	assign switch_units__recv__msg[1][12+:12] = route_units__send__msg[1][12+:12];
	assign route_units__send__rdy[1][1+:1] = switch_units__recv__rdy[1][1+:1];
	assign switch_units__recv__val[1][1+:1] = route_units__send__val[1][1+:1];
	assign switch_units__recv__msg[2][12+:12] = route_units__send__msg[1][0+:12];
	assign route_units__send__rdy[1][0+:1] = switch_units__recv__rdy[2][1+:1];
	assign switch_units__recv__val[2][1+:1] = route_units__send__val[1][0+:1];
	assign switch_units__recv__msg[0][0+:12] = route_units__send__msg[2][24+:12];
	assign route_units__send__rdy[2][2+:1] = switch_units__recv__rdy[0][0+:1];
	assign switch_units__recv__val[0][0+:1] = route_units__send__val[2][2+:1];
	assign switch_units__recv__msg[1][0+:12] = route_units__send__msg[2][12+:12];
	assign route_units__send__rdy[2][1+:1] = switch_units__recv__rdy[1][0+:1];
	assign switch_units__recv__val[1][0+:1] = route_units__send__val[2][1+:1];
	assign switch_units__recv__msg[2][0+:12] = route_units__send__msg[2][0+:12];
	assign route_units__send__rdy[2][0+:1] = switch_units__recv__rdy[2][0+:1];
	assign switch_units__recv__val[2][0+:1] = route_units__send__val[2][0+:1];
	assign output_units__recv__msg[0] = switch_units__send__msg[0];
	assign switch_units__send__rdy[0] = output_units__recv__rdy[0];
	assign output_units__recv__val[0] = switch_units__send__val[0];
	assign send__msg[24+:12] = output_units__send__msg[0];
	assign output_units__send__rdy[0] = send__rdy[2+:1];
	assign send__val[2+:1] = output_units__send__val[0];
	assign output_units__recv__msg[1] = switch_units__send__msg[1];
	assign switch_units__send__rdy[1] = output_units__recv__rdy[1];
	assign output_units__recv__val[1] = switch_units__send__val[1];
	assign send__msg[12+:12] = output_units__send__msg[1];
	assign output_units__send__rdy[1] = send__rdy[1+:1];
	assign send__val[1+:1] = output_units__send__val[1];
	assign output_units__recv__msg[2] = switch_units__send__msg[2];
	assign switch_units__send__rdy[2] = output_units__recv__rdy[2];
	assign output_units__recv__val[2] = switch_units__send__val[2];
	assign send__msg[0+:12] = output_units__send__msg[2];
	assign output_units__send__rdy[2] = send__rdy[0+:1];
	assign send__val[0+:1] = output_units__send__val[2];
endmodule
module Mux__85c058ea4b7b52c4 (
	clk,
	in_,
	out,
	reset,
	sel
);
	input wire [0:0] clk;
	input wire [69:0] in_;
	output reg [34:0] out;
	input wire [0:0] reset;
	input wire [0:0] sel;
	always @(*) begin : up_mux
		out = in_[(1 - sel) * 35+:35];
	end
endmodule
module BypassQueue1EntryRTL__6d09b133f21c8770 (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [0:0] count;
	input wire [0:0] reset;
	input wire [34:0] recv__msg;
	output reg [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [34:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	reg [34:0] entry;
	reg [0:0] full;
	wire [0:0] bypass_mux__clk;
	wire [69:0] bypass_mux__in_;
	wire [34:0] bypass_mux__out;
	wire [0:0] bypass_mux__reset;
	wire [0:0] bypass_mux__sel;
	Mux__85c058ea4b7b52c4 bypass_mux(
		.clk(bypass_mux__clk),
		.in_(bypass_mux__in_),
		.out(bypass_mux__out),
		.reset(bypass_mux__reset),
		.sel(bypass_mux__sel)
	);
	always @(*) begin : _lambda__s_dut_data_mem_recv_wdata_bypass_q_0__q_recv_rdy
		recv__rdy = ~full;
	end
	always @(*) begin : _lambda__s_dut_data_mem_recv_wdata_bypass_q_0__q_send_val
		send__val = full | recv__val;
	end
	always @(posedge clk) begin : ff_bypass1
		if (reset)
			full <= 1'd0;
		else
			full <= ~send__rdy & (full | recv__val);
		if ((~send__rdy & ~full) & recv__val)
			entry <= recv__msg;
	end
	assign bypass_mux__clk = clk;
	assign bypass_mux__reset = reset;
	assign bypass_mux__in_[35+:35] = recv__msg;
	assign bypass_mux__in_[0+:35] = entry;
	assign send__msg = bypass_mux__out;
	assign bypass_mux__sel = full;
	assign count = full;
endmodule
module BypassQueueRTL__7aa446127d3c2270 (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [0:0] count;
	input wire [0:0] reset;
	input wire [34:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [34:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] q__clk;
	wire [0:0] q__count;
	wire [0:0] q__reset;
	wire [34:0] q__recv__msg;
	wire [0:0] q__recv__rdy;
	wire [0:0] q__recv__val;
	wire [34:0] q__send__msg;
	wire [0:0] q__send__rdy;
	wire [0:0] q__send__val;
	BypassQueue1EntryRTL__6d09b133f21c8770 q(
		.clk(q__clk),
		.count(q__count),
		.reset(q__reset),
		.recv__msg(q__recv__msg),
		.recv__rdy(q__recv__rdy),
		.recv__val(q__recv__val),
		.send__msg(q__send__msg),
		.send__rdy(q__send__rdy),
		.send__val(q__send__val)
	);
	assign q__clk = clk;
	assign q__reset = reset;
	assign q__recv__msg = recv__msg;
	assign recv__rdy = q__recv__rdy;
	assign q__recv__val = recv__val;
	assign send__msg = q__send__msg;
	assign q__send__rdy = send__rdy;
	assign send__val = q__send__val;
	assign count = q__count;
endmodule
module RegisterFile__9ba561227ddc909a (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [1:0] raddr;
	output reg [34:0] rdata;
	input wire [0:0] reset;
	input wire [1:0] waddr;
	input wire [34:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [34:0] regs [0:3];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 35+:35] = regs[raddr[sv2v_cast_1(i) * 2+:2]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i) * 2+:2]] <= wdata[sv2v_cast_1(i) * 35+:35];
		end
	end
endmodule
module DataMemWithCrossbarRTL__e50b5d913fef7b11 (
	address_lower,
	address_upper,
	cgra_id,
	clk,
	reset,
	recv_from_noc_load_request__msg,
	recv_from_noc_load_request__rdy,
	recv_from_noc_load_request__val,
	recv_from_noc_load_response_pkt__msg,
	recv_from_noc_load_response_pkt__rdy,
	recv_from_noc_load_response_pkt__val,
	recv_from_noc_store_request__msg,
	recv_from_noc_store_request__rdy,
	recv_from_noc_store_request__val,
	recv_raddr__msg,
	recv_raddr__rdy,
	recv_raddr__val,
	recv_waddr__msg,
	recv_waddr__rdy,
	recv_waddr__val,
	recv_wdata__msg,
	recv_wdata__rdy,
	recv_wdata__val,
	send_rdata__msg,
	send_rdata__rdy,
	send_rdata__val,
	send_to_noc_load_request_pkt__msg,
	send_to_noc_load_request_pkt__rdy,
	send_to_noc_load_request_pkt__val,
	send_to_noc_load_response_pkt__msg,
	send_to_noc_load_response_pkt__rdy,
	send_to_noc_load_response_pkt__val,
	send_to_noc_store_pkt__msg,
	send_to_noc_store_pkt__rdy,
	send_to_noc_store_pkt__val
);
	input wire [2:0] address_lower;
	input wire [2:0] address_upper;
	input wire [1:0] cgra_id;
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [208:0] recv_from_noc_load_request__msg;
	output reg [0:0] recv_from_noc_load_request__rdy;
	input wire [0:0] recv_from_noc_load_request__val;
	input wire [208:0] recv_from_noc_load_response_pkt__msg;
	output reg [0:0] recv_from_noc_load_response_pkt__rdy;
	input wire [0:0] recv_from_noc_load_response_pkt__val;
	input wire [208:0] recv_from_noc_store_request__msg;
	output reg [0:0] recv_from_noc_store_request__rdy;
	input wire [0:0] recv_from_noc_store_request__val;
	input wire [5:0] recv_raddr__msg;
	output reg [1:0] recv_raddr__rdy;
	input wire [1:0] recv_raddr__val;
	input wire [5:0] recv_waddr__msg;
	output reg [1:0] recv_waddr__rdy;
	input wire [1:0] recv_waddr__val;
	input wire [69:0] recv_wdata__msg;
	output reg [1:0] recv_wdata__rdy;
	input wire [1:0] recv_wdata__val;
	output reg [69:0] send_rdata__msg;
	input wire [1:0] send_rdata__rdy;
	output reg [1:0] send_rdata__val;
	output reg [208:0] send_to_noc_load_request_pkt__msg;
	input wire [0:0] send_to_noc_load_request_pkt__rdy;
	output reg [0:0] send_to_noc_load_request_pkt__val;
	output reg [208:0] send_to_noc_load_response_pkt__msg;
	input wire [0:0] send_to_noc_load_response_pkt__rdy;
	output reg [0:0] send_to_noc_load_response_pkt__val;
	output reg [208:0] send_to_noc_store_pkt__msg;
	input wire [0:0] send_to_noc_store_pkt__rdy;
	output reg [0:0] send_to_noc_store_pkt__val;
	localparam [1:0] __const__num_xbar_in_rd_ports_at_assemble_xbar_pkt = 2'd3;
	localparam [1:0] __const__num_xbar_in_wr_ports_at_assemble_xbar_pkt = 2'd3;
	localparam [1:0] __const__num_rd_tiles_at_assemble_xbar_pkt = 2'd2;
	localparam [1:0] __const__per_bank_addr_nbits_at_assemble_xbar_pkt = 2'd2;
	localparam [1:0] __const__num_banks_per_cgra_at_assemble_xbar_pkt = 2'd2;
	localparam [1:0] __const__num_wr_tiles_at_assemble_xbar_pkt = 2'd2;
	localparam [1:0] __const__num_rd_tiles_at_update_all = 2'd2;
	localparam [1:0] __const__num_wr_tiles_at_update_all = 2'd2;
	localparam [1:0] __const__num_xbar_in_rd_ports_at_update_all = 2'd3;
	localparam [1:0] __const__num_xbar_in_wr_ports_at_update_all = 2'd3;
	localparam [1:0] __const__num_xbar_out_wr_ports_at_update_all = 2'd3;
	localparam [1:0] __const__num_xbar_out_rd_ports_at_update_all = 2'd3;
	localparam [1:0] __const__num_banks_per_cgra_at_update_all = 2'd2;
	localparam [2:0] __const__data_mem_size_per_bank_at_update_all = 3'd4;
	localparam [3:0] __const__CMD_LOAD_RESPONSE = 4'd11;
	localparam [3:0] __const__CMD_LOAD_REQUEST = 4'd10;
	localparam [3:0] __const__CMD_STORE_REQUEST = 4'd12;
	wire [1:0] idTo2d_x_lut [0:3];
	wire [0:0] idTo2d_y_lut [0:3];
	wire [0:0] initWrites [0:1][0:3];
	reg [1:0] init_mem_addr;
	reg [0:0] init_mem_done;
	wire [34:0] preload_data_per_bank [0:1][0:0];
	reg [11:0] rd_pkt [0:2];
	reg [0:0] send_to_noc_load_pending;
	reg [11:0] wr_pkt [0:2];
	wire [0:0] read_crossbar__clk;
	wire [35:0] read_crossbar__packet_on_input_units;
	wire [0:0] read_crossbar__reset;
	reg [35:0] read_crossbar__recv__msg;
	wire [2:0] read_crossbar__recv__rdy;
	reg [2:0] read_crossbar__recv__val;
	wire [35:0] read_crossbar__send__msg;
	reg [2:0] read_crossbar__send__rdy;
	wire [2:0] read_crossbar__send__val;
	XbarBypassQueueRTL__479e104af07e8511 read_crossbar(
		.clk(read_crossbar__clk),
		.packet_on_input_units(read_crossbar__packet_on_input_units),
		.reset(read_crossbar__reset),
		.recv__msg(read_crossbar__recv__msg),
		.recv__rdy(read_crossbar__recv__rdy),
		.recv__val(read_crossbar__recv__val),
		.send__msg(read_crossbar__send__msg),
		.send__rdy(read_crossbar__send__rdy),
		.send__val(read_crossbar__send__val)
	);
	wire [0:0] recv_wdata_bypass_q__clk [0:2];
	wire [0:0] recv_wdata_bypass_q__count [0:2];
	wire [0:0] recv_wdata_bypass_q__reset [0:2];
	reg [34:0] recv_wdata_bypass_q__recv__msg [0:2];
	wire [0:0] recv_wdata_bypass_q__recv__rdy [0:2];
	reg [0:0] recv_wdata_bypass_q__recv__val [0:2];
	wire [34:0] recv_wdata_bypass_q__send__msg [0:2];
	reg [0:0] recv_wdata_bypass_q__send__rdy [0:2];
	wire [0:0] recv_wdata_bypass_q__send__val [0:2];
	BypassQueueRTL__7aa446127d3c2270 recv_wdata_bypass_q__0(
		.clk(recv_wdata_bypass_q__clk[0]),
		.count(recv_wdata_bypass_q__count[0]),
		.reset(recv_wdata_bypass_q__reset[0]),
		.recv__msg(recv_wdata_bypass_q__recv__msg[0]),
		.recv__rdy(recv_wdata_bypass_q__recv__rdy[0]),
		.recv__val(recv_wdata_bypass_q__recv__val[0]),
		.send__msg(recv_wdata_bypass_q__send__msg[0]),
		.send__rdy(recv_wdata_bypass_q__send__rdy[0]),
		.send__val(recv_wdata_bypass_q__send__val[0])
	);
	BypassQueueRTL__7aa446127d3c2270 recv_wdata_bypass_q__1(
		.clk(recv_wdata_bypass_q__clk[1]),
		.count(recv_wdata_bypass_q__count[1]),
		.reset(recv_wdata_bypass_q__reset[1]),
		.recv__msg(recv_wdata_bypass_q__recv__msg[1]),
		.recv__rdy(recv_wdata_bypass_q__recv__rdy[1]),
		.recv__val(recv_wdata_bypass_q__recv__val[1]),
		.send__msg(recv_wdata_bypass_q__send__msg[1]),
		.send__rdy(recv_wdata_bypass_q__send__rdy[1]),
		.send__val(recv_wdata_bypass_q__send__val[1])
	);
	BypassQueueRTL__7aa446127d3c2270 recv_wdata_bypass_q__2(
		.clk(recv_wdata_bypass_q__clk[2]),
		.count(recv_wdata_bypass_q__count[2]),
		.reset(recv_wdata_bypass_q__reset[2]),
		.recv__msg(recv_wdata_bypass_q__recv__msg[2]),
		.recv__rdy(recv_wdata_bypass_q__recv__rdy[2]),
		.recv__val(recv_wdata_bypass_q__recv__val[2]),
		.send__msg(recv_wdata_bypass_q__send__msg[2]),
		.send__rdy(recv_wdata_bypass_q__send__rdy[2]),
		.send__val(recv_wdata_bypass_q__send__val[2])
	);
	wire [0:0] reg_file__clk [0:1];
	reg [1:0] reg_file__raddr [0:1];
	wire [34:0] reg_file__rdata [0:1];
	wire [0:0] reg_file__reset [0:1];
	reg [1:0] reg_file__waddr [0:1];
	reg [34:0] reg_file__wdata [0:1];
	reg [0:0] reg_file__wen [0:1];
	RegisterFile__9ba561227ddc909a reg_file__0(
		.clk(reg_file__clk[0]),
		.raddr(reg_file__raddr[0]),
		.rdata(reg_file__rdata[0]),
		.reset(reg_file__reset[0]),
		.waddr(reg_file__waddr[0]),
		.wdata(reg_file__wdata[0]),
		.wen(reg_file__wen[0])
	);
	RegisterFile__9ba561227ddc909a reg_file__1(
		.clk(reg_file__clk[1]),
		.raddr(reg_file__raddr[1]),
		.rdata(reg_file__rdata[1]),
		.reset(reg_file__reset[1]),
		.waddr(reg_file__waddr[1]),
		.wdata(reg_file__wdata[1]),
		.wen(reg_file__wen[1])
	);
	wire [0:0] write_crossbar__clk;
	wire [35:0] write_crossbar__packet_on_input_units;
	wire [0:0] write_crossbar__reset;
	reg [35:0] write_crossbar__recv__msg;
	wire [2:0] write_crossbar__recv__rdy;
	reg [2:0] write_crossbar__recv__val;
	wire [35:0] write_crossbar__send__msg;
	reg [2:0] write_crossbar__send__rdy;
	wire [2:0] write_crossbar__send__val;
	XbarBypassQueueRTL__479e104af07e8511 write_crossbar(
		.clk(write_crossbar__clk),
		.packet_on_input_units(write_crossbar__packet_on_input_units),
		.reset(write_crossbar__reset),
		.recv__msg(write_crossbar__recv__msg),
		.recv__rdy(write_crossbar__recv__rdy),
		.recv__val(write_crossbar__recv__val),
		.send__msg(write_crossbar__send__msg),
		.send__rdy(write_crossbar__send__rdy),
		.send__val(write_crossbar__send__val)
	);
	reg [2:0] __tmpvar__assemble_xbar_pkt_recv_raddr;
	reg [1:0] __tmpvar__assemble_xbar_pkt_bank_index_load_local;
	reg [2:0] __tmpvar__assemble_xbar_pkt_recv_raddr_from_noc;
	reg [1:0] __tmpvar__assemble_xbar_pkt_bank_index_load_from_noc;
	reg [2:0] __tmpvar__assemble_xbar_pkt_recv_waddr;
	reg [1:0] __tmpvar__assemble_xbar_pkt_bank_index_store_local;
	reg [2:0] __tmpvar__assemble_xbar_pkt_recv_waddr_from_noc;
	reg [1:0] __tmpvar__assemble_xbar_pkt_bank_index_store_from_noc;
	reg [1:0] __tmpvar__update_all_from_cgra_id;
	reg [2:0] __tmpvar__update_all_from_tile_id;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : assemble_xbar_pkt
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_xbar_in_rd_ports_at_assemble_xbar_pkt; i = i + 1'd1)
				rd_pkt[sv2v_cast_2(i)] = {sv2v_cast_2(i), 10'h000};
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_xbar_in_wr_ports_at_assemble_xbar_pkt; i = i + 1'd1)
				wr_pkt[sv2v_cast_2(i)] = {sv2v_cast_2(i), 10'h000};
		end
		if (init_mem_done != 1'd0) begin
			begin : sv2v_autoblock_3
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_rd_tiles_at_assemble_xbar_pkt; i = i + 1'd1)
					begin
						__tmpvar__assemble_xbar_pkt_recv_raddr = recv_raddr__msg[(1 - sv2v_cast_1(i)) * 3+:3];
						if ((__tmpvar__assemble_xbar_pkt_recv_raddr >= address_lower) & (__tmpvar__assemble_xbar_pkt_recv_raddr <= address_upper))
							__tmpvar__assemble_xbar_pkt_bank_index_load_local = sv2v_cast_2((__tmpvar__assemble_xbar_pkt_recv_raddr - address_lower) >> __const__per_bank_addr_nbits_at_assemble_xbar_pkt);
						else
							__tmpvar__assemble_xbar_pkt_bank_index_load_local = 2'd2;
						rd_pkt[sv2v_cast_2(i)] = {sv2v_cast_2(i), __tmpvar__assemble_xbar_pkt_bank_index_load_local, __tmpvar__assemble_xbar_pkt_recv_raddr, cgra_id, 3'd0};
					end
			end
			__tmpvar__assemble_xbar_pkt_recv_raddr_from_noc = recv_from_noc_load_request__msg[143-:3];
			if ((__tmpvar__assemble_xbar_pkt_recv_raddr_from_noc >= address_lower) & (__tmpvar__assemble_xbar_pkt_recv_raddr_from_noc <= address_upper))
				__tmpvar__assemble_xbar_pkt_bank_index_load_from_noc = sv2v_cast_2((__tmpvar__assemble_xbar_pkt_recv_raddr_from_noc - address_lower) >> __const__per_bank_addr_nbits_at_assemble_xbar_pkt);
			else
				__tmpvar__assemble_xbar_pkt_bank_index_load_from_noc = 2'd2;
			rd_pkt[__const__num_rd_tiles_at_assemble_xbar_pkt] = {__const__num_rd_tiles_at_assemble_xbar_pkt, __tmpvar__assemble_xbar_pkt_bank_index_load_from_noc, __tmpvar__assemble_xbar_pkt_recv_raddr_from_noc, recv_from_noc_load_request__msg[208-:2], recv_from_noc_load_request__msg[198-:3]};
			begin : sv2v_autoblock_4
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_wr_tiles_at_assemble_xbar_pkt; i = i + 1'd1)
					begin
						__tmpvar__assemble_xbar_pkt_recv_waddr = recv_waddr__msg[(1 - sv2v_cast_1(i)) * 3+:3];
						if ((__tmpvar__assemble_xbar_pkt_recv_waddr >= address_lower) & (__tmpvar__assemble_xbar_pkt_recv_waddr <= address_upper))
							__tmpvar__assemble_xbar_pkt_bank_index_store_local = sv2v_cast_2((__tmpvar__assemble_xbar_pkt_recv_waddr - address_lower) >> __const__per_bank_addr_nbits_at_assemble_xbar_pkt);
						else
							__tmpvar__assemble_xbar_pkt_bank_index_store_local = 2'd2;
						wr_pkt[sv2v_cast_2(i)] = {sv2v_cast_2(i), __tmpvar__assemble_xbar_pkt_bank_index_store_local, __tmpvar__assemble_xbar_pkt_recv_waddr, 5'h00};
					end
			end
			__tmpvar__assemble_xbar_pkt_recv_waddr_from_noc = recv_from_noc_store_request__msg[143-:3];
			if ((__tmpvar__assemble_xbar_pkt_recv_waddr_from_noc >= address_lower) & (__tmpvar__assemble_xbar_pkt_recv_waddr_from_noc <= address_upper))
				__tmpvar__assemble_xbar_pkt_bank_index_store_from_noc = sv2v_cast_2((__tmpvar__assemble_xbar_pkt_recv_waddr_from_noc - address_lower) >> __const__per_bank_addr_nbits_at_assemble_xbar_pkt);
			else
				__tmpvar__assemble_xbar_pkt_bank_index_store_from_noc = 2'd2;
			wr_pkt[__const__num_wr_tiles_at_assemble_xbar_pkt] = {__const__num_wr_tiles_at_assemble_xbar_pkt, __tmpvar__assemble_xbar_pkt_bank_index_store_from_noc, __tmpvar__assemble_xbar_pkt_recv_waddr_from_noc, 5'h00};
		end
	end
	always @(*) begin : update_all
		begin : sv2v_autoblock_5
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_rd_tiles_at_update_all; i = i + 1'd1)
				recv_raddr__rdy[1 - sv2v_cast_1(i)+:1] = 1'd0;
		end
		recv_from_noc_load_request__rdy = 1'd0;
		begin : sv2v_autoblock_6
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_wr_tiles_at_update_all; i = i + 1'd1)
				begin
					recv_waddr__rdy[1 - sv2v_cast_1(i)+:1] = 1'd0;
					recv_wdata_bypass_q__send__rdy[sv2v_cast_2(i)] = 1'd0;
				end
		end
		recv_from_noc_store_request__rdy = 1'd0;
		recv_wdata_bypass_q__send__rdy[__const__num_wr_tiles_at_update_all] = 1'd0;
		begin : sv2v_autoblock_7
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_rd_tiles_at_update_all; i = i + 1'd1)
				begin
					send_rdata__val[1 - sv2v_cast_1(i)+:1] = 1'd0;
					send_rdata__msg[(1 - sv2v_cast_1(i)) * 35+:35] = 35'h000000000;
				end
		end
		send_to_noc_load_response_pkt__val = 1'd0;
		send_to_noc_load_response_pkt__msg = 209'h00000000000000000000000000000000000000000000000000000;
		begin : sv2v_autoblock_8
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_wr_tiles_at_update_all; i = i + 1'd1)
				begin
					recv_wdata__rdy[1 - sv2v_cast_1(i)+:1] = 1'd0;
					recv_wdata_bypass_q__recv__val[sv2v_cast_2(i)] = 1'd0;
					recv_wdata_bypass_q__recv__msg[sv2v_cast_2(i)] = 35'h000000000;
				end
		end
		recv_wdata_bypass_q__recv__val[__const__num_wr_tiles_at_update_all] = 1'd0;
		recv_wdata_bypass_q__recv__msg[__const__num_wr_tiles_at_update_all] = 35'h000000000;
		send_to_noc_store_pkt__msg = 209'h00000000000000000000000000000000000000000000000000000;
		send_to_noc_store_pkt__val = 1'd0;
		begin : sv2v_autoblock_9
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_xbar_in_rd_ports_at_update_all; i = i + 1'd1)
				begin
					read_crossbar__recv__val[2 - sv2v_cast_2(i)+:1] = 1'd0;
					read_crossbar__recv__msg[(2 - sv2v_cast_2(i)) * 12+:12] = 12'h000;
				end
		end
		recv_from_noc_load_response_pkt__rdy = 1'd0;
		begin : sv2v_autoblock_10
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_xbar_in_wr_ports_at_update_all; i = i + 1'd1)
				begin
					write_crossbar__recv__val[2 - sv2v_cast_2(i)+:1] = 1'd0;
					write_crossbar__recv__msg[(2 - sv2v_cast_2(i)) * 12+:12] = 12'h000;
				end
		end
		begin : sv2v_autoblock_11
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_xbar_out_wr_ports_at_update_all; i = i + 1'd1)
				write_crossbar__send__rdy[2 - sv2v_cast_2(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_12
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_xbar_out_rd_ports_at_update_all; i = i + 1'd1)
				read_crossbar__send__rdy[2 - sv2v_cast_2(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_13
			reg [31:0] b;
			for (b = 1'd0; b < __const__num_banks_per_cgra_at_update_all; b = b + 1'd1)
				reg_file__raddr[sv2v_cast_1(b)][1'd0 * 2+:2] = 2'd0;
		end
		send_to_noc_load_request_pkt__msg = 209'h00000000000000000000000000000000000000000000000000000;
		send_to_noc_load_request_pkt__val = 1'd0;
		if (init_mem_done == 1'd0) begin : sv2v_autoblock_14
			reg [31:0] b;
			for (b = 1'd0; b < __const__num_banks_per_cgra_at_update_all; b = b + 1'd1)
				begin
					reg_file__waddr[sv2v_cast_1(b)][1'd0 * 2+:2] = init_mem_addr;
					reg_file__wdata[sv2v_cast_1(b)][1'd0 * 35+:35] = preload_data_per_bank[sv2v_cast_1(b)][sv2v_cast_1(init_mem_addr)];
					reg_file__wen[sv2v_cast_1(b)][1'd0+:1] = 1'd1;
				end
		end
		else begin
			begin : sv2v_autoblock_15
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_wr_tiles_at_update_all; i = i + 1'd1)
					begin
						recv_wdata__rdy[1 - sv2v_cast_1(i)+:1] = recv_wdata_bypass_q__recv__rdy[sv2v_cast_2(i)];
						recv_wdata_bypass_q__recv__val[sv2v_cast_2(i)] = recv_wdata__val[1 - sv2v_cast_1(i)+:1];
						recv_wdata_bypass_q__recv__msg[sv2v_cast_2(i)] = recv_wdata__msg[(1 - sv2v_cast_1(i)) * 35+:35];
					end
			end
			recv_from_noc_store_request__rdy = recv_wdata_bypass_q__recv__rdy[__const__num_wr_tiles_at_update_all];
			recv_wdata_bypass_q__recv__val[__const__num_wr_tiles_at_update_all] = recv_from_noc_store_request__val;
			recv_wdata_bypass_q__recv__msg[__const__num_wr_tiles_at_update_all] = recv_from_noc_store_request__msg[178-:35];
			begin : sv2v_autoblock_16
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_rd_tiles_at_update_all; i = i + 1'd1)
					begin
						read_crossbar__recv__val[2 - sv2v_cast_2(i)+:1] = recv_raddr__val[1 - sv2v_cast_1(i)+:1];
						read_crossbar__recv__msg[(2 - sv2v_cast_2(i)) * 12+:12] = rd_pkt[sv2v_cast_2(i)];
						recv_raddr__rdy[1 - sv2v_cast_1(i)+:1] = read_crossbar__recv__rdy[2 - sv2v_cast_2(i)+:1];
					end
			end
			read_crossbar__recv__val[2 - __const__num_rd_tiles_at_update_all+:1] = recv_from_noc_load_request__val;
			read_crossbar__recv__msg[(2 - __const__num_rd_tiles_at_update_all) * 12+:12] = rd_pkt[__const__num_rd_tiles_at_update_all];
			recv_from_noc_load_request__rdy = read_crossbar__recv__rdy[2 - __const__num_rd_tiles_at_update_all+:1];
			begin : sv2v_autoblock_17
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_wr_tiles_at_update_all; i = i + 1'd1)
					begin
						write_crossbar__recv__val[2 - sv2v_cast_2(i)+:1] = recv_waddr__val[1 - sv2v_cast_1(i)+:1];
						write_crossbar__recv__msg[(2 - sv2v_cast_2(i)) * 12+:12] = wr_pkt[sv2v_cast_2(i)];
						recv_waddr__rdy[1 - sv2v_cast_1(i)+:1] = write_crossbar__recv__rdy[2 - sv2v_cast_2(i)+:1];
					end
			end
			write_crossbar__recv__val[2 - __const__num_wr_tiles_at_update_all+:1] = recv_from_noc_store_request__val;
			write_crossbar__recv__msg[(2 - __const__num_wr_tiles_at_update_all) * 12+:12] = wr_pkt[__const__num_wr_tiles_at_update_all];
			recv_from_noc_store_request__rdy = write_crossbar__recv__rdy[2 - __const__num_wr_tiles_at_update_all+:1];
			begin : sv2v_autoblock_18
				reg [31:0] b;
				for (b = 1'd0; b < __const__num_banks_per_cgra_at_update_all; b = b + 1'd1)
					begin
						read_crossbar__send__rdy[2 - sv2v_cast_2(b)+:1] = 1'd1;
						reg_file__raddr[sv2v_cast_1(b)][1'd0 * 2+:2] = sv2v_cast_2(read_crossbar__send__msg[((2 - sv2v_cast_2(b)) * 12) + 7-:3] % __const__data_mem_size_per_bank_at_update_all);
					end
			end
			begin : sv2v_autoblock_19
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_xbar_in_rd_ports_at_update_all; i = i + 1'd1)
					if ((read_crossbar__send__msg[((2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]) * 12) + 11-:2] == sv2v_cast_2(i)) & (read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2] < __const__num_banks_per_cgra_at_update_all)) begin
						if (sv2v_cast_2(i) < __const__num_rd_tiles_at_update_all) begin
							send_rdata__msg[(1 - sv2v_cast_1(sv2v_cast_2(i))) * 35+:35] = reg_file__rdata[sv2v_cast_1(read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2])][1'd0 * 35+:35];
							send_rdata__val[1 - sv2v_cast_1(sv2v_cast_2(i))+:1] = read_crossbar__send__val[2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]+:1];
						end
						else begin
							__tmpvar__update_all_from_cgra_id = read_crossbar__send__msg[((2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]) * 12) + 4-:2];
							__tmpvar__update_all_from_tile_id = read_crossbar__send__msg[((2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]) * 12) + 2-:3];
							send_to_noc_load_response_pkt__msg = {cgra_id, __tmpvar__update_all_from_cgra_id, idTo2d_x_lut[cgra_id], idTo2d_y_lut[cgra_id], idTo2d_x_lut[__tmpvar__update_all_from_cgra_id], idTo2d_y_lut[__tmpvar__update_all_from_cgra_id], 3'd0, read_crossbar__send__msg[((2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]) * 12) + 2-:3], 10'h000, __const__CMD_LOAD_RESPONSE, reg_file__rdata[sv2v_cast_1(read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2])][(1'd0 * 35) + 34-:32], reg_file__rdata[sv2v_cast_1(read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2])][(1'd0 * 35) + 2], 2'h0, read_crossbar__send__msg[((2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]) * 12) + 7-:3], 141'h000000000000000000000000000000000000};
							send_to_noc_load_response_pkt__val = read_crossbar__send__val[2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]+:1];
						end
					end
					else if ((read_crossbar__send__msg[((2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]) * 12) + 11-:2] == sv2v_cast_2(i)) & (read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2] >= __const__num_banks_per_cgra_at_update_all)) begin
						send_rdata__msg[(1 - sv2v_cast_1(sv2v_cast_2(i))) * 35+:35] = recv_from_noc_load_response_pkt__msg[178-:35];
						send_rdata__val[1 - sv2v_cast_1(sv2v_cast_2(i))+:1] = read_crossbar__send__val[2 - read_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]+:1] & recv_from_noc_load_response_pkt__val;
					end
			end
			send_to_noc_load_request_pkt__msg = {cgra_id, 2'd0, idTo2d_x_lut[cgra_id], idTo2d_y_lut[cgra_id], 19'h00000, __const__CMD_LOAD_REQUEST, 35'd0, read_crossbar__send__msg[((2 - __const__num_banks_per_cgra_at_update_all) * 12) + 7-:3], 141'h000000000000000000000000000000000000};
			send_to_noc_load_request_pkt__val = read_crossbar__send__val[2 - __const__num_banks_per_cgra_at_update_all+:1] & ~send_to_noc_load_pending;
			recv_from_noc_load_response_pkt__rdy = read_crossbar__send__val[2 - __const__num_banks_per_cgra_at_update_all+:1];
			read_crossbar__send__rdy[2 - __const__num_banks_per_cgra_at_update_all+:1] = recv_from_noc_load_response_pkt__val;
			begin : sv2v_autoblock_20
				reg [31:0] b;
				for (b = 1'd0; b < __const__num_banks_per_cgra_at_update_all; b = b + 1'd1)
					begin
						reg_file__wen[sv2v_cast_1(b)][1'd0+:1] = 1'd0;
						reg_file__waddr[sv2v_cast_1(b)][1'd0 * 2+:2] = sv2v_cast_2(write_crossbar__send__msg[((2 - sv2v_cast_2(b)) * 12) + 7-:3] % __const__data_mem_size_per_bank_at_update_all);
						reg_file__wdata[sv2v_cast_1(b)][1'd0 * 35+:35] = recv_wdata_bypass_q__send__msg[write_crossbar__send__msg[((2 - sv2v_cast_2(b)) * 12) + 11-:2]];
						write_crossbar__send__rdy[2 - sv2v_cast_2(b)+:1] = 1'd1;
						reg_file__wen[sv2v_cast_1(b)][1'd0+:1] = write_crossbar__send__val[2 - sv2v_cast_2(b)+:1];
					end
			end
			begin : sv2v_autoblock_21
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_xbar_in_wr_ports_at_update_all; i = i + 1'd1)
					recv_wdata_bypass_q__send__rdy[sv2v_cast_2(i)] = write_crossbar__send__val[2 - write_crossbar__packet_on_input_units[((2 - sv2v_cast_2(i)) * 12) + 9-:2]+:1];
			end
			send_to_noc_store_pkt__msg = {cgra_id, 2'd0, idTo2d_x_lut[cgra_id], idTo2d_y_lut[cgra_id], 19'h00000, __const__CMD_STORE_REQUEST, recv_wdata_bypass_q__send__msg[write_crossbar__send__msg[((2 - __const__num_banks_per_cgra_at_update_all) * 12) + 11-:2]][34-:32], recv_wdata_bypass_q__send__msg[write_crossbar__send__msg[((2 - __const__num_banks_per_cgra_at_update_all) * 12) + 11-:2]][2], 2'h0, write_crossbar__send__msg[((2 - __const__num_banks_per_cgra_at_update_all) * 12) + 7-:3], 141'h000000000000000000000000000000000000};
			send_to_noc_store_pkt__val = write_crossbar__send__val[2 - __const__num_banks_per_cgra_at_update_all+:1];
			write_crossbar__send__rdy[2 - __const__num_banks_per_cgra_at_update_all+:1] = send_to_noc_store_pkt__rdy;
		end
	end
	always @(posedge clk) begin : update_init_index_once
		if (reset) begin
			init_mem_done <= 1'd0;
			init_mem_addr <= 2'd0;
		end
		else if (init_mem_done == 1'd0) begin
			init_mem_done <= 1'd1;
			init_mem_addr <= 2'd0;
		end
	end
	always @(posedge clk) begin : update_remote_load_pending
		if (reset)
			send_to_noc_load_pending <= 1'd0;
		else if (recv_from_noc_load_response_pkt__val)
			send_to_noc_load_pending <= 1'd0;
		else if (send_to_noc_load_request_pkt__val & send_to_noc_load_request_pkt__rdy)
			send_to_noc_load_pending <= 1'd1;
	end
	assign reg_file__clk[0] = clk;
	assign reg_file__reset[0] = reset;
	assign reg_file__clk[1] = clk;
	assign reg_file__reset[1] = reset;
	assign read_crossbar__clk = clk;
	assign read_crossbar__reset = reset;
	assign write_crossbar__clk = clk;
	assign write_crossbar__reset = reset;
	assign recv_wdata_bypass_q__clk[0] = clk;
	assign recv_wdata_bypass_q__reset[0] = reset;
	assign recv_wdata_bypass_q__clk[1] = clk;
	assign recv_wdata_bypass_q__reset[1] = reset;
	assign recv_wdata_bypass_q__clk[2] = clk;
	assign recv_wdata_bypass_q__reset[2] = reset;
	assign idTo2d_x_lut[0] = 2'd0;
	assign idTo2d_y_lut[0] = 1'd0;
	assign idTo2d_x_lut[1] = 2'd1;
	assign idTo2d_y_lut[1] = 1'd0;
	assign idTo2d_x_lut[2] = 2'd2;
	assign idTo2d_y_lut[2] = 1'd0;
	assign idTo2d_x_lut[3] = 2'd3;
	assign idTo2d_y_lut[3] = 1'd0;
	assign preload_data_per_bank[0][0] = 35'h000000000;
	assign preload_data_per_bank[1][0] = 35'h000000000;
endmodule
module RegisterFile__e6e244c14d4afbbe (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [2:0] raddr;
	output reg [34:0] rdata;
	input wire [0:0] reset;
	input wire [2:0] waddr;
	input wire [34:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [34:0] regs [0:5];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 35+:35] = regs[raddr[sv2v_cast_1(i) * 3+:3]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i) * 3+:3]] <= wdata[sv2v_cast_1(i) * 35+:35];
		end
	end
endmodule
module ConstQueueDynamicRTL__8f4d11f2dd80f063 (
	clk,
	ctrl_proceed,
	reset,
	recv_const__msg,
	recv_const__rdy,
	recv_const__val,
	send_const__msg,
	send_const__rdy,
	send_const__val
);
	input wire [0:0] clk;
	input wire [0:0] ctrl_proceed;
	input wire [0:0] reset;
	input wire [34:0] recv_const__msg;
	output reg [0:0] recv_const__rdy;
	input wire [0:0] recv_const__val;
	output wire [34:0] send_const__msg;
	input wire [0:0] send_const__rdy;
	output reg [0:0] send_const__val;
	localparam [2:0] __const__const_mem_size_at_load_const = 3'd6;
	localparam [2:0] __const__const_mem_size_at_update_wr_cur = 3'd6;
	reg [2:0] rd_cur;
	reg [2:0] wr_cur;
	wire [0:0] reg_file__clk;
	wire [2:0] reg_file__raddr;
	wire [34:0] reg_file__rdata;
	wire [0:0] reg_file__reset;
	reg [2:0] reg_file__waddr;
	reg [34:0] reg_file__wdata;
	reg [0:0] reg_file__wen;
	RegisterFile__e6e244c14d4afbbe reg_file(
		.clk(reg_file__clk),
		.raddr(reg_file__raddr),
		.rdata(reg_file__rdata),
		.reset(reg_file__reset),
		.waddr(reg_file__waddr),
		.wdata(reg_file__wdata),
		.wen(reg_file__wen)
	);
	reg [0:0] __tmpvar__load_const_not_full;
	reg [0:0] __tmpvar__update_wr_cur_not_full;
	always @(*) begin : load_const
		reg_file__waddr[1'd0 * 3+:3] = 3'd0;
		reg_file__wdata[1'd0 * 35+:35] = 35'h000000000;
		reg_file__wen[1'd0+:1] = 1'd0;
		__tmpvar__load_const_not_full = wr_cur < __const__const_mem_size_at_load_const;
		recv_const__rdy = __tmpvar__load_const_not_full;
		if (recv_const__val & __tmpvar__load_const_not_full) begin
			reg_file__waddr[1'd0 * 3+:3] = wr_cur;
			reg_file__wdata[1'd0 * 35+:35] = recv_const__msg;
			reg_file__wen[1'd0+:1] = 1'd1;
		end
	end
	always @(*) begin : update_send_val
		if (rd_cur < wr_cur)
			send_const__val = 1'd1;
		else
			send_const__val = 1'd0;
	end
	always @(posedge clk) begin : update_rd_cur
		if (reset)
			rd_cur <= 3'd0;
		else if (send_const__rdy & ctrl_proceed)
			if (rd_cur < (wr_cur - 3'd1))
				rd_cur <= rd_cur + 3'd1;
			else
				rd_cur <= 3'd0;
	end
	always @(posedge clk) begin : update_wr_cur
		__tmpvar__update_wr_cur_not_full = wr_cur < __const__const_mem_size_at_update_wr_cur;
		if (reset)
			wr_cur <= 3'd0;
		else if (recv_const__val & __tmpvar__update_wr_cur_not_full)
			wr_cur <= wr_cur + 3'd1;
	end
	assign reg_file__clk = clk;
	assign reg_file__reset = reset;
	assign send_const__msg = reg_file__rdata[0+:35];
	assign reg_file__raddr[0+:3] = rd_cur;
endmodule
module RegisterFile__3ffc5c38f361fd13 (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [2:0] raddr;
	output reg [137:0] rdata;
	input wire [0:0] reset;
	input wire [2:0] waddr;
	input wire [137:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [137:0] regs [0:5];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 138+:138] = regs[raddr[sv2v_cast_1(i) * 3+:3]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i) * 3+:3]] <= wdata[sv2v_cast_1(i) * 138+:138];
		end
	end
endmodule
module CtrlMemDynamicRTL__3bcda19edfae4ca2 (
	cgra_id,
	clk,
	ctrl_addr_outport,
	prologue_count_outport_fu,
	prologue_count_outport_fu_crossbar,
	prologue_count_outport_routing_crossbar,
	reset,
	tile_id,
	recv_pkt_from_controller__msg,
	recv_pkt_from_controller__rdy,
	recv_pkt_from_controller__val,
	send_ctrl__msg,
	send_ctrl__rdy,
	send_ctrl__val,
	send_pkt_to_controller__msg,
	send_pkt_to_controller__rdy,
	send_pkt_to_controller__val
);
	input wire [1:0] cgra_id;
	input wire [0:0] clk;
	output reg [2:0] ctrl_addr_outport;
	output reg [2:0] prologue_count_outport_fu;
	output reg [35:0] prologue_count_outport_fu_crossbar;
	output reg [143:0] prologue_count_outport_routing_crossbar;
	input wire [0:0] reset;
	input wire [2:0] tile_id;
	input wire [207:0] recv_pkt_from_controller__msg;
	output wire [0:0] recv_pkt_from_controller__rdy;
	input wire [0:0] recv_pkt_from_controller__val;
	output wire [137:0] send_ctrl__msg;
	input wire [0:0] send_ctrl__rdy;
	output reg [0:0] send_ctrl__val;
	output reg [207:0] send_pkt_to_controller__msg;
	input wire [0:0] send_pkt_to_controller__rdy;
	output reg [0:0] send_pkt_to_controller__val;
	localparam [2:0] __const__num_fu_inports_at_update_msg = 3'd4;
	localparam [3:0] __const__num_routing_outports_at_update_msg = 4'd12;
	localparam [1:0] __const__CMD_CONFIG = 2'd3;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_FU = 3'd4;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR = 3'd5;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR = 3'd6;
	localparam [0:0] __const__CMD_LAUNCH = 1'd0;
	localparam [1:0] __const__CMD_TERMINATE = 2'd2;
	localparam [0:0] __const__CMD_PAUSE = 1'd1;
	localparam [2:0] __const__CMD_CONFIG_TOTAL_CTRL_COUNT = 3'd7;
	localparam [3:0] __const__CMD_CONFIG_COUNT_PER_ITER = 4'd8;
	localparam [3:0] __const__CMD_CONFIG_CTRL_LOWER_BOUND = 4'd9;
	localparam [2:0] __const__num_tiles_at_update_send_out_signal = 3'd4;
	localparam [3:0] __const__CMD_COMPLETE = 4'd14;
	localparam [5:0] __const__OPT_START = 6'd0;
	localparam [2:0] __const__ctrl_mem_size_at_update_raddr_and_fu_prologue = 3'd6;
	localparam [2:0] __const__ctrl_mem_size_at_update_prologue_outport = 3'd6;
	localparam [3:0] __const__num_tile_inports_at_update_prologue_outport = 4'd8;
	localparam [1:0] __const__num_fu_outports_at_update_prologue_outport = 2'd2;
	localparam [2:0] __const__ctrl_mem_size_at_update_prologue_reg = 3'd6;
	localparam [3:0] __const__num_tile_inports_at_update_prologue_reg = 4'd8;
	localparam [1:0] __const__num_fu_outports_at_update_prologue_reg = 2'd2;
	localparam [2:0] __const__ctrl_count_per_iter_at_update_ctrl_count_per_iter = 3'd6;
	localparam [2:0] __const__total_ctrl_steps_at_update_total_ctrl_steps = 3'd6;
	reg [2:0] ctrl_count_lower_bound;
	reg [2:0] ctrl_count_per_iter_val;
	reg [2:0] ctrl_count_upper_bound;
	reg [2:0] prologue_count_reg_fu [0:5];
	reg [2:0] prologue_count_reg_fu_crossbar [0:5][0:1];
	reg [2:0] prologue_count_reg_routing_crossbar [0:5][0:7];
	reg [0:0] sent_complete;
	reg [0:0] start_iterate_ctrl;
	reg [10:0] times;
	reg [10:0] total_ctrl_steps_val;
	wire [0:0] recv_pkt_queue__clk;
	wire [1:0] recv_pkt_queue__count;
	wire [0:0] recv_pkt_queue__reset;
	wire [207:0] recv_pkt_queue__recv__msg;
	wire [0:0] recv_pkt_queue__recv__rdy;
	wire [0:0] recv_pkt_queue__recv__val;
	wire [207:0] recv_pkt_queue__send__msg;
	reg [0:0] recv_pkt_queue__send__rdy;
	wire [0:0] recv_pkt_queue__send__val;
	NormalQueueRTL__55c6fcde46462f0c recv_pkt_queue(
		.clk(recv_pkt_queue__clk),
		.count(recv_pkt_queue__count),
		.reset(recv_pkt_queue__reset),
		.recv__msg(recv_pkt_queue__recv__msg),
		.recv__rdy(recv_pkt_queue__recv__rdy),
		.recv__val(recv_pkt_queue__recv__val),
		.send__msg(recv_pkt_queue__send__msg),
		.send__rdy(recv_pkt_queue__send__rdy),
		.send__val(recv_pkt_queue__send__val)
	);
	wire [0:0] reg_file__clk;
	reg [2:0] reg_file__raddr;
	wire [137:0] reg_file__rdata;
	wire [0:0] reg_file__reset;
	reg [2:0] reg_file__waddr;
	reg [137:0] reg_file__wdata;
	reg [0:0] reg_file__wen;
	RegisterFile__3ffc5c38f361fd13 reg_file(
		.clk(reg_file__clk),
		.raddr(reg_file__raddr),
		.rdata(reg_file__rdata),
		.reset(reg_file__reset),
		.waddr(reg_file__waddr),
		.wdata(reg_file__wdata),
		.wen(reg_file__wen)
	);
	reg [3:0] __tmpvar__update_prologue_reg_temp_routing_crossbar_in;
	reg [1:0] __tmpvar__update_prologue_reg_temp_fu_crossbar_in;
	always @(*) begin : update_ctrl_addr_outport
		ctrl_addr_outport = reg_file__raddr[1'd0 * 3+:3];
	end
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	always @(*) begin : update_msg
		recv_pkt_queue__send__rdy = 1'd0;
		reg_file__wen[1'd0+:1] = 1'd0;
		reg_file__waddr[1'd0 * 3+:3] = recv_pkt_queue__send__msg[2-:3];
		reg_file__wdata[(1'd0 * 138) + 137-:6] = 6'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_fu_inports_at_update_msg; i = i + 1'd1)
				begin
					reg_file__wdata[(1'd0 * 138) + (120 + (sv2v_cast_2(i) * 3))+:3] = 3'd0;
					reg_file__wdata[(1'd0 * 138) + (36 + (sv2v_cast_2(i) * 2))+:2] = recv_pkt_queue__send__msg[39 + (sv2v_cast_2(i) * 2)+:2];
					reg_file__wdata[(1'd0 * 138) + (20 + (sv2v_cast_2(i) * 4))+:4] = recv_pkt_queue__send__msg[23 + (sv2v_cast_2(i) * 4)+:4];
					reg_file__wdata[(1'd0 * 138) + (16 + sv2v_cast_2(i))+:1] = recv_pkt_queue__send__msg[19 + sv2v_cast_2(i)+:1];
					reg_file__wdata[(1'd0 * 138) + (0 + (sv2v_cast_2(i) * 4))+:4] = recv_pkt_queue__send__msg[3 + (sv2v_cast_2(i) * 4)+:4];
				end
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_routing_outports_at_update_msg; i = i + 1'd1)
				begin
					reg_file__wdata[(1'd0 * 138) + (72 + (sv2v_cast_4(i) * 4))+:4] = 4'd0;
					reg_file__wdata[(1'd0 * 138) + (48 + (sv2v_cast_4(i) * 2))+:2] = 2'd0;
				end
		end
		reg_file__wdata[(1'd0 * 138) + 47-:3] = recv_pkt_queue__send__msg[50-:3];
		reg_file__wdata[(1'd0 * 138) + 44] = 1'd0;
		if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG))) begin
			reg_file__wen[1'd0+:1] = 1'd1;
			reg_file__waddr[1'd0 * 3+:3] = recv_pkt_queue__send__msg[2-:3];
			reg_file__wdata[(1'd0 * 138) + 137-:6] = recv_pkt_queue__send__msg[140-:6];
			begin : sv2v_autoblock_3
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_fu_inports_at_update_msg; i = i + 1'd1)
					begin
						reg_file__wdata[(1'd0 * 138) + (120 + (sv2v_cast_2(i) * 3))+:3] = recv_pkt_queue__send__msg[123 + (sv2v_cast_2(i) * 3)+:3];
						reg_file__wdata[(1'd0 * 138) + (36 + (sv2v_cast_2(i) * 2))+:2] = recv_pkt_queue__send__msg[39 + (sv2v_cast_2(i) * 2)+:2];
						reg_file__wdata[(1'd0 * 138) + (20 + (sv2v_cast_2(i) * 4))+:4] = recv_pkt_queue__send__msg[23 + (sv2v_cast_2(i) * 4)+:4];
						reg_file__wdata[(1'd0 * 138) + (16 + sv2v_cast_2(i))+:1] = recv_pkt_queue__send__msg[19 + sv2v_cast_2(i)+:1];
						reg_file__wdata[(1'd0 * 138) + (0 + (sv2v_cast_2(i) * 4))+:4] = recv_pkt_queue__send__msg[3 + (sv2v_cast_2(i) * 4)+:4];
					end
			end
			begin : sv2v_autoblock_4
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_routing_outports_at_update_msg; i = i + 1'd1)
					begin
						reg_file__wdata[(1'd0 * 138) + (72 + (sv2v_cast_4(i) * 4))+:4] = recv_pkt_queue__send__msg[75 + (sv2v_cast_4(i) * 4)+:4];
						reg_file__wdata[(1'd0 * 138) + (48 + (sv2v_cast_4(i) * 2))+:2] = recv_pkt_queue__send__msg[51 + (sv2v_cast_4(i) * 2)+:2];
					end
			end
			reg_file__wdata[(1'd0 * 138) + 47-:3] = recv_pkt_queue__send__msg[50-:3];
			reg_file__wdata[(1'd0 * 138) + 44] = recv_pkt_queue__send__msg[47];
		end
		if (((((((((((recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG)) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU))) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR))) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR))) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_LAUNCH))) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_TERMINATE))) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_PAUSE))) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_TOTAL_CTRL_COUNT))) | (recv_pkt_queue__send__msg[182-:4] == __const__CMD_CONFIG_COUNT_PER_ITER)) | (recv_pkt_queue__send__msg[182-:4] == __const__CMD_CONFIG_CTRL_LOWER_BOUND)) | (recv_pkt_queue__send__msg[182-:4] == __const__CMD_CONFIG_COUNT_PER_ITER))
			recv_pkt_queue__send__rdy = 1'd1;
	end
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : update_prologue_outport
		prologue_count_outport_fu = prologue_count_reg_fu[reg_file__raddr[1'd0 * 3+:3]];
		begin : sv2v_autoblock_5
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_outport; addr = addr + 1'd1)
				begin
					begin : sv2v_autoblock_6
						reg [31:0] i;
						for (i = 1'd0; i < __const__num_tile_inports_at_update_prologue_outport; i = i + 1'd1)
							prologue_count_outport_routing_crossbar[(((5 - sv2v_cast_3(addr)) * 8) + (7 - sv2v_cast_3(i))) * 3+:3] = prologue_count_reg_routing_crossbar[sv2v_cast_3(addr)][sv2v_cast_3(i)];
					end
					begin : sv2v_autoblock_7
						reg [31:0] i;
						for (i = 1'd0; i < __const__num_fu_outports_at_update_prologue_outport; i = i + 1'd1)
							prologue_count_outport_fu_crossbar[(((5 - sv2v_cast_3(addr)) * 2) + (1 - sv2v_cast_1(i))) * 3+:3] = prologue_count_reg_fu_crossbar[sv2v_cast_3(addr)][sv2v_cast_1(i)];
					end
				end
		end
	end
	always @(*) begin : update_send_out_signal
		send_ctrl__val = 1'd0;
		send_pkt_to_controller__val = 1'd0;
		send_pkt_to_controller__msg = {3'd0, __const__num_tiles_at_update_send_out_signal, 19'h00000, __const__CMD_COMPLETE, 179'h000000000000000000000000000000000000000000000};
		if (start_iterate_ctrl == 1'd1)
			if (((total_ctrl_steps_val > 11'd0) & (times == total_ctrl_steps_val)) | (reg_file__rdata[(1'd0 * 138) + 137-:6] == __const__OPT_START)) begin
				send_ctrl__val = 1'd0;
				if (((~sent_complete & (total_ctrl_steps_val > 11'd0)) & (times == total_ctrl_steps_val)) & start_iterate_ctrl) begin
					send_pkt_to_controller__msg = {tile_id, __const__num_tiles_at_update_send_out_signal, 19'h00000, __const__CMD_COMPLETE, 179'h000000000000000000000000000000000000000000000};
					send_pkt_to_controller__val = 1'd1;
				end
			end
			else
				send_ctrl__val = 1'd1;
		if (recv_pkt_queue__send__val & ((recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_PAUSE)) | (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_TERMINATE))))
			send_ctrl__val = 1'd0;
	end
	always @(*) begin : update_upper_bound
		ctrl_count_upper_bound = ctrl_count_lower_bound + ctrl_count_per_iter_val;
	end
	always @(posedge clk) begin : issue_complete
		if (reset)
			sent_complete <= 1'd0;
		else begin
			if (send_pkt_to_controller__val & send_pkt_to_controller__rdy)
				sent_complete <= 1'd1;
			if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_LAUNCH)))
				sent_complete <= 1'd0;
		end
	end
	always @(posedge clk) begin : update_ctrl_count_per_iter
		if (reset)
			ctrl_count_per_iter_val <= 3'd6;
		else if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == __const__CMD_CONFIG_COUNT_PER_ITER))
			ctrl_count_per_iter_val <= sv2v_cast_3(recv_pkt_queue__send__msg[178-:32]);
	end
	always @(posedge clk) begin : update_lower_bound
		if (reset)
			ctrl_count_lower_bound <= 3'd0;
		else if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == __const__CMD_CONFIG_CTRL_LOWER_BOUND))
			ctrl_count_lower_bound <= sv2v_cast_3(recv_pkt_queue__send__msg[178-:32]);
	end
	always @(posedge clk) begin : update_prologue_reg
		if (reset) begin : sv2v_autoblock_8
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_reg; addr = addr + 1'd1)
				begin
					begin : sv2v_autoblock_9
						reg [31:0] i;
						for (i = 1'd0; i < __const__num_tile_inports_at_update_prologue_reg; i = i + 1'd1)
							prologue_count_reg_routing_crossbar[sv2v_cast_3(addr)][sv2v_cast_3(i)] <= 3'd0;
					end
					begin : sv2v_autoblock_10
						reg [31:0] i;
						for (i = 1'd0; i < __const__num_fu_outports_at_update_prologue_reg; i = i + 1'd1)
							prologue_count_reg_fu_crossbar[sv2v_cast_3(addr)][sv2v_cast_1(i)] <= 3'd0;
					end
				end
		end
		else if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR))) begin
			__tmpvar__update_prologue_reg_temp_routing_crossbar_in = recv_pkt_queue__send__msg[75 + (4'd0 * 4)+:4];
			prologue_count_reg_routing_crossbar[recv_pkt_queue__send__msg[2-:3]][sv2v_cast_3(__tmpvar__update_prologue_reg_temp_routing_crossbar_in)] <= sv2v_cast_3(recv_pkt_queue__send__msg[178-:32]);
		end
		else if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR))) begin
			__tmpvar__update_prologue_reg_temp_fu_crossbar_in = recv_pkt_queue__send__msg[51 + (4'd0 * 2)+:2];
			prologue_count_reg_fu_crossbar[recv_pkt_queue__send__msg[2-:3]][sv2v_cast_1(__tmpvar__update_prologue_reg_temp_fu_crossbar_in)] <= sv2v_cast_3(recv_pkt_queue__send__msg[178-:32]);
		end
	end
	always @(posedge clk) begin : update_raddr_and_fu_prologue
		if (reset) begin
			times <= 11'd0;
			reg_file__raddr[1'd0 * 3+:3] <= 3'd0;
			begin : sv2v_autoblock_11
				reg [31:0] i;
				for (i = 1'd0; i < __const__ctrl_mem_size_at_update_raddr_and_fu_prologue; i = i + 1'd1)
					prologue_count_reg_fu[sv2v_cast_3(i)] <= 3'd0;
			end
		end
		else if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == __const__CMD_CONFIG_CTRL_LOWER_BOUND))
			reg_file__raddr[1'd0 * 3+:3] <= sv2v_cast_3(recv_pkt_queue__send__msg[178-:32]);
		else begin
			if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU)))
				prologue_count_reg_fu[recv_pkt_queue__send__msg[2-:3]] <= sv2v_cast_3(recv_pkt_queue__send__msg[178-:32]);
			if (start_iterate_ctrl == 1'd1) begin
				if ((((total_ctrl_steps_val == 11'd0) | (times < total_ctrl_steps_val)) & send_ctrl__rdy) & send_ctrl__val)
					times <= times + 11'd1;
				if (send_ctrl__rdy & send_ctrl__val) begin
					if (reg_file__raddr[1'd0 * 3+:3] == (ctrl_count_upper_bound - 3'd1))
						reg_file__raddr[1'd0 * 3+:3] <= ctrl_count_lower_bound;
					else
						reg_file__raddr[1'd0 * 3+:3] <= reg_file__raddr[1'd0 * 3+:3] + 3'd1;
					if (prologue_count_reg_fu[reg_file__raddr[1'd0 * 3+:3]] > 3'd0)
						prologue_count_reg_fu[reg_file__raddr[1'd0 * 3+:3]] <= prologue_count_reg_fu[reg_file__raddr[1'd0 * 3+:3]] - 3'd1;
				end
			end
		end
	end
	function automatic [10:0] sv2v_cast_11;
		input reg [10:0] inp;
		sv2v_cast_11 = inp;
	endfunction
	always @(posedge clk) begin : update_total_ctrl_steps
		if (reset)
			total_ctrl_steps_val <= 11'd6;
		else if (recv_pkt_queue__send__val & (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_TOTAL_CTRL_COUNT)))
			total_ctrl_steps_val <= sv2v_cast_11(recv_pkt_queue__send__msg[178-:32]);
	end
	always @(posedge clk) begin : update_whether_we_can_iterate_ctrl
		if (reset)
			start_iterate_ctrl <= 1'd0;
		else if (recv_pkt_queue__send__val)
			if (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_LAUNCH))
				start_iterate_ctrl <= 1'd1;
			else if (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_TERMINATE))
				start_iterate_ctrl <= 1'd0;
			else if (recv_pkt_queue__send__msg[182-:4] == sv2v_cast_4(__const__CMD_PAUSE))
				start_iterate_ctrl <= 1'd0;
	end
	assign reg_file__clk = clk;
	assign reg_file__reset = reset;
	assign recv_pkt_queue__clk = clk;
	assign recv_pkt_queue__reset = reset;
	assign send_ctrl__msg = reg_file__rdata[0+:138];
	assign recv_pkt_queue__recv__msg = recv_pkt_from_controller__msg;
	assign recv_pkt_from_controller__rdy = recv_pkt_queue__recv__rdy;
	assign recv_pkt_queue__recv__val = recv_pkt_from_controller__val;
endmodule
module MemUnitRTL__a685aceb001a2483 (
	clk,
	reset,
	from_mem_rdata__msg,
	from_mem_rdata__rdy,
	from_mem_rdata__val,
	recv_const__msg,
	recv_const__rdy,
	recv_const__val,
	recv_in__msg,
	recv_in__rdy,
	recv_in__val,
	recv_opt__msg,
	recv_opt__rdy,
	recv_opt__val,
	send_out__msg,
	send_out__rdy,
	send_out__val,
	to_mem_raddr__msg,
	to_mem_raddr__rdy,
	to_mem_raddr__val,
	to_mem_waddr__msg,
	to_mem_waddr__rdy,
	to_mem_waddr__val,
	to_mem_wdata__msg,
	to_mem_wdata__rdy,
	to_mem_wdata__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [34:0] from_mem_rdata__msg;
	output reg [0:0] from_mem_rdata__rdy;
	input wire [0:0] from_mem_rdata__val;
	input wire [34:0] recv_const__msg;
	output reg [0:0] recv_const__rdy;
	input wire [0:0] recv_const__val;
	input wire [139:0] recv_in__msg;
	output reg [3:0] recv_in__rdy;
	input wire [3:0] recv_in__val;
	input wire [137:0] recv_opt__msg;
	output reg [0:0] recv_opt__rdy;
	input wire [0:0] recv_opt__val;
	output reg [69:0] send_out__msg;
	input wire [1:0] send_out__rdy;
	output reg [1:0] send_out__val;
	output reg [2:0] to_mem_raddr__msg;
	input wire [0:0] to_mem_raddr__rdy;
	output reg [0:0] to_mem_raddr__val;
	output reg [2:0] to_mem_waddr__msg;
	input wire [0:0] to_mem_waddr__rdy;
	output reg [0:0] to_mem_waddr__val;
	output reg [34:0] to_mem_wdata__msg;
	input wire [0:0] to_mem_wdata__rdy;
	output reg [0:0] to_mem_wdata__val;
	localparam [2:0] __const__num_inports_at_comb_logic = 3'd4;
	localparam [1:0] __const__num_outports_at_comb_logic = 2'd2;
	localparam [5:0] __const__OPT_LD = 6'd12;
	localparam [5:0] __const__OPT_LD_CONST = 6'd28;
	localparam [5:0] __const__OPT_STR = 6'd13;
	localparam [5:0] __const__OPT_STR_CONST = 6'd58;
	reg [2:0] in0;
	wire [1:0] in0_idx;
	reg [2:0] in1;
	wire [1:0] in1_idx;
	reg [0:0] reached_vector_factor;
	reg [0:0] recv_all_val;
	wire [3:0] recv_in_val_vector;
	reg [7:0] vector_factor_counter;
	wire [2:0] vector_factor_power;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : comb_logic
		recv_all_val = 1'd0;
		in0 = 3'd0;
		in1 = 3'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_comb_logic; i = i + 1'd1)
				recv_in__rdy[3 - sv2v_cast_2(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_comb_logic; i = i + 1'd1)
				begin
					send_out__val[1 - sv2v_cast_1(i)+:1] = 1'd0;
					send_out__msg[(1 - sv2v_cast_1(i)) * 35+:35] = 35'h000000000;
				end
		end
		recv_const__rdy = 1'd0;
		recv_opt__rdy = 1'd0;
		if (recv_opt__val) begin
			if (recv_opt__msg[120 + (2'd0 * 3)+:3] != 3'd0)
				in0 = recv_opt__msg[120 + (2'd0 * 3)+:3] - 3'd1;
			if (recv_opt__msg[120 + (2'd1 * 3)+:3] != 3'd0)
				in1 = recv_opt__msg[120 + (2'd1 * 3)+:3] - 3'd1;
		end
		to_mem_waddr__val = 1'd0;
		to_mem_waddr__msg = 3'd0;
		to_mem_wdata__val = 1'd0;
		to_mem_wdata__msg = 35'h000000000;
		to_mem_raddr__val = 1'd0;
		to_mem_raddr__msg = 3'd0;
		from_mem_rdata__rdy = 1'd0;
		if (recv_opt__val)
			if (recv_opt__msg[137-:6] == __const__OPT_LD) begin
				recv_all_val = recv_in__val[3 - in0_idx+:1];
				recv_in__rdy[3 - in0_idx+:1] = recv_all_val & to_mem_raddr__rdy;
				to_mem_raddr__msg = sv2v_cast_3(recv_in__msg[((3 - in0_idx) * 35) + ((3 + 5'd2) >= (3 + 5'd0) ? 3 + 5'd2 : ((3 + 5'd2) + ((3 + 5'd2) >= (3 + 5'd0) ? ((3 + 5'd2) - (3 + 5'd0)) + 1 : ((3 + 5'd0) - (3 + 5'd2)) + 1)) - 1)-:((3 + 5'd2) >= (3 + 5'd0) ? ((3 + 5'd2) - (3 + 5'd0)) + 1 : ((3 + 5'd0) - (3 + 5'd2)) + 1)]);
				to_mem_raddr__val = recv_all_val;
				from_mem_rdata__rdy = send_out__rdy[(1 - 1'd0) + 0+:1];
				send_out__val[(1 - 1'd0) + 0+:1] = from_mem_rdata__val;
				send_out__msg[((1 - 1'd0) + 0) * 35+:35] = from_mem_rdata__msg;
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = (recv_in__msg[((3 - in0_idx) * 35) + 2] & from_mem_rdata__msg[2]) & reached_vector_factor;
				recv_opt__rdy = send_out__rdy[(1 - 1'd0) + 0+:1] & from_mem_rdata__val;
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_LD_CONST) begin
				recv_all_val = recv_const__val;
				recv_const__rdy = recv_all_val & to_mem_raddr__rdy;
				to_mem_raddr__msg = sv2v_cast_3(recv_const__msg[3 + 5'd2:3 + 5'd0]);
				to_mem_raddr__val = recv_all_val;
				from_mem_rdata__rdy = send_out__rdy[(1 - 1'd0) + 0+:1];
				send_out__val[(1 - 1'd0) + 0+:1] = from_mem_rdata__val;
				send_out__msg[((1 - 1'd0) + 0) * 35+:35] = from_mem_rdata__msg;
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = (recv_const__msg[2] & from_mem_rdata__msg[2]) & reached_vector_factor;
				recv_opt__rdy = send_out__rdy[(1 - 1'd0) + 0+:1] & from_mem_rdata__val;
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_STR) begin
				recv_all_val = recv_in__val[3 - in0_idx+:1] & recv_in__val[3 - in1_idx+:1];
				recv_in__rdy[3 - in0_idx+:1] = (recv_all_val & to_mem_waddr__rdy) & to_mem_wdata__rdy;
				recv_in__rdy[3 - in1_idx+:1] = (recv_all_val & to_mem_waddr__rdy) & to_mem_wdata__rdy;
				to_mem_waddr__msg = sv2v_cast_3(recv_in__msg[(((3 - 2'd0) + 0) * 35) + ((3 + 5'd2) >= (3 + 5'd0) ? 3 + 5'd2 : ((3 + 5'd2) + ((3 + 5'd2) >= (3 + 5'd0) ? ((3 + 5'd2) - (3 + 5'd0)) + 1 : ((3 + 5'd0) - (3 + 5'd2)) + 1)) - 1)-:((3 + 5'd2) >= (3 + 5'd0) ? ((3 + 5'd2) - (3 + 5'd0)) + 1 : ((3 + 5'd0) - (3 + 5'd2)) + 1)]);
				to_mem_waddr__val = recv_all_val;
				to_mem_wdata__msg = recv_in__msg[(3 - in1_idx) * 35+:35];
				to_mem_wdata__msg[2] = (recv_in__msg[((3 - in0_idx) * 35) + 2] & recv_in__msg[((3 - in1_idx) * 35) + 2]) & reached_vector_factor;
				to_mem_wdata__val = recv_all_val;
				send_out__val[(1 - 1'd0) + 0+:1] = 1'd0;
				recv_opt__rdy = (recv_all_val & to_mem_waddr__rdy) & to_mem_wdata__rdy;
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_STR_CONST) begin
				recv_all_val = recv_in__val[3 - in0_idx+:1] & recv_const__val;
				recv_const__rdy = (recv_all_val & to_mem_waddr__rdy) & to_mem_wdata__rdy;
				recv_in__rdy[3 - in0_idx+:1] = (recv_all_val & to_mem_waddr__rdy) & to_mem_wdata__rdy;
				to_mem_waddr__msg = sv2v_cast_3(recv_const__msg[3 + 5'd2:3 + 5'd0]);
				to_mem_waddr__val = (recv_all_val & recv_in__msg[((3 - in0_idx) * 35) + 2]) & recv_const__msg[2];
				to_mem_wdata__msg = recv_in__msg[(3 - in0_idx) * 35+:35];
				to_mem_wdata__msg[2] = (recv_in__msg[((3 - in0_idx) * 35) + 2] & recv_const__msg[2]) & reached_vector_factor;
				to_mem_wdata__val = (recv_all_val & recv_in__msg[((3 - in0_idx) * 35) + 2]) & recv_const__msg[2];
				send_out__val[(1 - 1'd0) + 0+:1] = 1'd0;
				recv_opt__rdy = (recv_all_val & to_mem_waddr__rdy) & to_mem_wdata__rdy;
			end
			else begin
				begin : sv2v_autoblock_3
					reg [31:0] j;
					for (j = 1'd0; j < __const__num_outports_at_comb_logic; j = j + 1'd1)
						send_out__val[1 - sv2v_cast_1(j)+:1] = 1'd0;
				end
				recv_opt__rdy = 1'd0;
				recv_in__rdy[3 - in0_idx+:1] = 1'd0;
				recv_in__rdy[3 - in1_idx+:1] = 1'd0;
			end
	end
	always @(*) begin : update_reached_vector_factor
		reached_vector_factor = 1'd0;
		if (recv_opt__val & ((vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power})) >= (8'd1 << {{5 {1'b0}}, recv_opt__msg[47-:3]})))
			reached_vector_factor = 1'd1;
	end
	always @(posedge clk) begin : update_vector_factor_counter
		if (reset)
			vector_factor_counter <= 8'd0;
		else if (recv_opt__val)
			if (recv_opt__msg[44] & ((vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power})) < (8'd1 << {{5 {1'b0}}, recv_opt__msg[47-:3]})))
				vector_factor_counter <= vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power});
			else if (recv_opt__msg[44] & reached_vector_factor)
				vector_factor_counter <= 8'd0;
	end
	assign in0_idx = in0[1:0];
	assign in1_idx = in1[1:0];
	assign vector_factor_power = 3'd0;
endmodule
module AdderRTL__a685aceb001a2483 (
	clk,
	reset,
	from_mem_rdata__msg,
	from_mem_rdata__rdy,
	from_mem_rdata__val,
	recv_const__msg,
	recv_const__rdy,
	recv_const__val,
	recv_in__msg,
	recv_in__rdy,
	recv_in__val,
	recv_opt__msg,
	recv_opt__rdy,
	recv_opt__val,
	send_out__msg,
	send_out__rdy,
	send_out__val,
	to_mem_raddr__msg,
	to_mem_raddr__rdy,
	to_mem_raddr__val,
	to_mem_waddr__msg,
	to_mem_waddr__rdy,
	to_mem_waddr__val,
	to_mem_wdata__msg,
	to_mem_wdata__rdy,
	to_mem_wdata__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [34:0] from_mem_rdata__msg;
	output reg [0:0] from_mem_rdata__rdy;
	input wire [0:0] from_mem_rdata__val;
	input wire [34:0] recv_const__msg;
	output reg [0:0] recv_const__rdy;
	input wire [0:0] recv_const__val;
	input wire [139:0] recv_in__msg;
	output reg [3:0] recv_in__rdy;
	input wire [3:0] recv_in__val;
	input wire [137:0] recv_opt__msg;
	output reg [0:0] recv_opt__rdy;
	input wire [0:0] recv_opt__val;
	output reg [69:0] send_out__msg;
	input wire [1:0] send_out__rdy;
	output reg [1:0] send_out__val;
	output reg [2:0] to_mem_raddr__msg;
	input wire [0:0] to_mem_raddr__rdy;
	output reg [0:0] to_mem_raddr__val;
	output reg [2:0] to_mem_waddr__msg;
	input wire [0:0] to_mem_waddr__rdy;
	output reg [0:0] to_mem_waddr__val;
	output reg [34:0] to_mem_wdata__msg;
	input wire [0:0] to_mem_wdata__rdy;
	output reg [0:0] to_mem_wdata__val;
	localparam [34:0] const_zero = 35'h000000000;
	localparam [5:0] __const__OPT_START = 6'd0;
	localparam [0:0] __const__latency_at_proceed_latency = 1'd1;
	localparam [2:0] __const__num_inports_at_comb_logic = 3'd4;
	localparam [1:0] __const__num_outports_at_comb_logic = 2'd2;
	localparam [5:0] __const__OPT_ADD = 6'd2;
	localparam [5:0] __const__OPT_ADD_CONST = 6'd25;
	localparam [5:0] __const__OPT_INC = 6'd3;
	localparam [5:0] __const__OPT_SUB = 6'd4;
	localparam [5:0] __const__OPT_PAS = 6'd31;
	reg [2:0] in0;
	wire [1:0] in0_idx;
	reg [2:0] in1;
	wire [1:0] in1_idx;
	reg [0:0] latency;
	reg [0:0] reached_vector_factor;
	reg [0:0] recv_all_val;
	reg [7:0] vector_factor_counter;
	wire [2:0] vector_factor_power;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : comb_logic
		recv_all_val = 1'd0;
		in0 = 3'd0;
		in1 = 3'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_comb_logic; i = i + 1'd1)
				recv_in__rdy[3 - sv2v_cast_2(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_comb_logic; i = i + 1'd1)
				begin
					send_out__val[1 - sv2v_cast_1(i)+:1] = 1'd0;
					send_out__msg[(1 - sv2v_cast_1(i)) * 35+:35] = 35'h000000000;
				end
		end
		recv_const__rdy = 1'd0;
		recv_opt__rdy = 1'd0;
		if (recv_opt__val) begin
			if (recv_opt__msg[120 + (2'd0 * 3)+:3] != 3'd0)
				in0 = recv_opt__msg[120 + (2'd0 * 3)+:3] - 3'd1;
			if (recv_opt__msg[120 + (2'd1 * 3)+:3] != 3'd0)
				in1 = recv_opt__msg[120 + (2'd1 * 3)+:3] - 3'd1;
		end
		if (recv_opt__val)
			if (recv_opt__msg[137-:6] == __const__OPT_ADD) begin
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 34-:32] = recv_in__msg[((3 - in0_idx) * 35) + 34-:32] + recv_in__msg[((3 - in1_idx) * 35) + 34-:32];
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = (recv_in__msg[((3 - in0_idx) * 35) + 2] & recv_in__msg[((3 - in1_idx) * 35) + 2]) & reached_vector_factor;
				recv_all_val = recv_in__val[3 - in0_idx+:1] & recv_in__val[3 - in1_idx+:1];
				send_out__val[(1 - 1'd0) + 0+:1] = recv_all_val;
				recv_in__rdy[3 - in0_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_in__rdy[3 - in1_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_opt__rdy = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_ADD_CONST) begin
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 34-:32] = recv_in__msg[((3 - in0_idx) * 35) + 34-:32] + recv_const__msg[34-:32];
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = (recv_in__msg[((3 - in0_idx) * 35) + 2] & recv_const__msg[2]) & reached_vector_factor;
				recv_const__rdy = send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_all_val = recv_in__val[3 - in0_idx+:1] & recv_const__val;
				send_out__val[(1 - 1'd0) + 0+:1] = recv_all_val;
				recv_in__rdy[3 - in0_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_const__rdy = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_opt__rdy = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_INC) begin
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 34-:32] = recv_in__msg[((3 - in0_idx) * 35) + 34-:32] + 32'd1;
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = recv_in__msg[((3 - in0_idx) * 35) + 2] & reached_vector_factor;
				recv_all_val = recv_in__val[3 - in0_idx+:1];
				send_out__val[(1 - 1'd0) + 0+:1] = recv_all_val;
				recv_in__rdy[3 - in0_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_opt__rdy = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_SUB) begin
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 34-:32] = recv_in__msg[((3 - in0_idx) * 35) + 34-:32] - recv_in__msg[((3 - in1_idx) * 35) + 34-:32];
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = (recv_in__msg[((3 - in0_idx) * 35) + 2] & recv_in__msg[((3 - in1_idx) * 35) + 2]) & reached_vector_factor;
				recv_all_val = recv_in__val[3 - in0_idx+:1] & recv_in__val[3 - in1_idx+:1];
				send_out__val[(1 - 1'd0) + 0+:1] = recv_all_val;
				recv_in__rdy[3 - in0_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_in__rdy[3 - in1_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_opt__rdy = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
			end
			else if (recv_opt__msg[137-:6] == __const__OPT_PAS) begin
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 34-:32] = recv_in__msg[((3 - in0_idx) * 35) + 34-:32];
				send_out__msg[(((1 - 1'd0) + 0) * 35) + 2] = recv_in__msg[((3 - in0_idx) * 35) + 2] & reached_vector_factor;
				recv_all_val = recv_in__val[3 - in0_idx+:1];
				send_out__val[(1 - 1'd0) + 0+:1] = recv_all_val;
				recv_in__rdy[3 - in0_idx+:1] = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
				recv_opt__rdy = recv_all_val & send_out__rdy[(1 - 1'd0) + 0+:1];
			end
			else begin
				begin : sv2v_autoblock_3
					reg [31:0] j;
					for (j = 1'd0; j < __const__num_outports_at_comb_logic; j = j + 1'd1)
						send_out__val[1 - sv2v_cast_1(j)+:1] = 1'd0;
				end
				recv_opt__rdy = 1'd0;
				recv_in__rdy[3 - in0_idx+:1] = 1'd0;
				recv_in__rdy[3 - in1_idx+:1] = 1'd0;
			end
	end
	always @(*) begin : update_mem
		to_mem_waddr__val = 1'd0;
		to_mem_wdata__val = 1'd0;
		to_mem_wdata__msg = const_zero;
		to_mem_waddr__msg = 3'd0;
		to_mem_raddr__msg = 3'd0;
		to_mem_raddr__val = 1'd0;
		from_mem_rdata__rdy = 1'd0;
	end
	always @(*) begin : update_reached_vector_factor
		reached_vector_factor = 1'd0;
		if (recv_opt__val & ((vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power})) >= (8'd1 << {{5 {1'b0}}, recv_opt__msg[47-:3]})))
			reached_vector_factor = 1'd1;
	end
	always @(posedge clk) begin : proceed_latency
		if (recv_opt__msg[137-:6] == __const__OPT_START)
			latency <= 1'd0;
		else if (latency == (__const__latency_at_proceed_latency - 1'd1))
			latency <= 1'd0;
		else
			latency <= latency + 1'd1;
	end
	always @(posedge clk) begin : update_vector_factor_counter
		if (reset)
			vector_factor_counter <= 8'd0;
		else if (recv_opt__val)
			if (recv_opt__msg[44] & ((vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power})) < (8'd1 << {{5 {1'b0}}, recv_opt__msg[47-:3]})))
				vector_factor_counter <= vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power});
			else if (recv_opt__msg[44] & reached_vector_factor)
				vector_factor_counter <= 8'd0;
	end
	assign vector_factor_power = 3'd0;
	assign in0_idx = in0[1:0];
	assign in1_idx = in1[1:0];
endmodule
module NahRTL__a685aceb001a2483 (
	clk,
	reset,
	from_mem_rdata__msg,
	from_mem_rdata__rdy,
	from_mem_rdata__val,
	recv_const__msg,
	recv_const__rdy,
	recv_const__val,
	recv_in__msg,
	recv_in__rdy,
	recv_in__val,
	recv_opt__msg,
	recv_opt__rdy,
	recv_opt__val,
	send_out__msg,
	send_out__rdy,
	send_out__val,
	to_mem_raddr__msg,
	to_mem_raddr__rdy,
	to_mem_raddr__val,
	to_mem_waddr__msg,
	to_mem_waddr__rdy,
	to_mem_waddr__val,
	to_mem_wdata__msg,
	to_mem_wdata__rdy,
	to_mem_wdata__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [34:0] from_mem_rdata__msg;
	output reg [0:0] from_mem_rdata__rdy;
	input wire [0:0] from_mem_rdata__val;
	input wire [34:0] recv_const__msg;
	output reg [0:0] recv_const__rdy;
	input wire [0:0] recv_const__val;
	input wire [139:0] recv_in__msg;
	output reg [3:0] recv_in__rdy;
	input wire [3:0] recv_in__val;
	input wire [137:0] recv_opt__msg;
	output reg [0:0] recv_opt__rdy;
	input wire [0:0] recv_opt__val;
	output reg [69:0] send_out__msg;
	input wire [1:0] send_out__rdy;
	output reg [1:0] send_out__val;
	output reg [2:0] to_mem_raddr__msg;
	input wire [0:0] to_mem_raddr__rdy;
	output reg [0:0] to_mem_raddr__val;
	output reg [2:0] to_mem_waddr__msg;
	input wire [0:0] to_mem_waddr__rdy;
	output reg [0:0] to_mem_waddr__val;
	output reg [34:0] to_mem_wdata__msg;
	input wire [0:0] to_mem_wdata__rdy;
	output reg [0:0] to_mem_wdata__val;
	localparam [34:0] const_zero = 35'h000000000;
	localparam [5:0] __const__OPT_START = 6'd0;
	localparam [0:0] __const__latency_at_proceed_latency = 1'd1;
	localparam [2:0] __const__num_inports_at_comb_logic = 3'd4;
	localparam [1:0] __const__num_outports_at_comb_logic = 2'd2;
	localparam [5:0] __const__OPT_NAH = 6'd1;
	reg [0:0] latency;
	reg [0:0] reached_vector_factor;
	reg [7:0] vector_factor_counter;
	wire [2:0] vector_factor_power;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : comb_logic
		recv_const__rdy = 1'd0;
		recv_opt__rdy = 1'd0;
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_comb_logic; i = i + 1'd1)
				recv_in__rdy[3 - sv2v_cast_2(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_comb_logic; i = i + 1'd1)
				begin
					send_out__val[1 - sv2v_cast_1(i)+:1] = 1'd0;
					send_out__msg[(1 - sv2v_cast_1(i)) * 35+:35] = 35'h000000000;
				end
		end
		if (recv_opt__msg[137-:6] == __const__OPT_NAH)
			recv_opt__rdy = 1'd1;
		else begin
			begin : sv2v_autoblock_3
				reg [31:0] j;
				for (j = 1'd0; j < __const__num_outports_at_comb_logic; j = j + 1'd1)
					send_out__val[1 - sv2v_cast_1(j)+:1] = 1'd0;
			end
			recv_opt__rdy = 1'd0;
		end
	end
	always @(*) begin : update_mem
		to_mem_waddr__val = 1'd0;
		to_mem_wdata__val = 1'd0;
		to_mem_wdata__msg = const_zero;
		to_mem_waddr__msg = 3'd0;
		to_mem_raddr__msg = 3'd0;
		to_mem_raddr__val = 1'd0;
		from_mem_rdata__rdy = 1'd0;
	end
	always @(*) begin : update_reached_vector_factor
		reached_vector_factor = 1'd0;
		if (recv_opt__val & ((vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power})) >= (8'd1 << {{5 {1'b0}}, recv_opt__msg[47-:3]})))
			reached_vector_factor = 1'd1;
	end
	always @(posedge clk) begin : proceed_latency
		if (recv_opt__msg[137-:6] == __const__OPT_START)
			latency <= 1'd0;
		else if (latency == (__const__latency_at_proceed_latency - 1'd1))
			latency <= 1'd0;
		else
			latency <= latency + 1'd1;
	end
	always @(posedge clk) begin : update_vector_factor_counter
		if (reset)
			vector_factor_counter <= 8'd0;
		else if (recv_opt__val)
			if (recv_opt__msg[44] & ((vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power})) < (8'd1 << {{5 {1'b0}}, recv_opt__msg[47-:3]})))
				vector_factor_counter <= vector_factor_counter + (8'd1 << {{5 {1'b0}}, vector_factor_power});
			else if (recv_opt__msg[44] & reached_vector_factor)
				vector_factor_counter <= 8'd0;
	end
	assign vector_factor_power = 3'd0;
endmodule
module FlexibleFuRTL__91ead62b2a3425ea (
	clk,
	prologue_count_inport,
	reset,
	tile_id,
	from_mem_rdata__msg,
	from_mem_rdata__rdy,
	from_mem_rdata__val,
	recv_const__msg,
	recv_const__rdy,
	recv_const__val,
	recv_in__msg,
	recv_in__rdy,
	recv_in__val,
	recv_opt__msg,
	recv_opt__rdy,
	recv_opt__val,
	send_out__msg,
	send_out__rdy,
	send_out__val,
	to_mem_raddr__msg,
	to_mem_raddr__rdy,
	to_mem_raddr__val,
	to_mem_waddr__msg,
	to_mem_waddr__rdy,
	to_mem_waddr__val,
	to_mem_wdata__msg,
	to_mem_wdata__rdy,
	to_mem_wdata__val
);
	input wire [0:0] clk;
	input wire [2:0] prologue_count_inport;
	input wire [0:0] reset;
	input wire [2:0] tile_id;
	input wire [104:0] from_mem_rdata__msg;
	output wire [2:0] from_mem_rdata__rdy;
	input wire [2:0] from_mem_rdata__val;
	input wire [34:0] recv_const__msg;
	output reg [0:0] recv_const__rdy;
	input wire [0:0] recv_const__val;
	input wire [139:0] recv_in__msg;
	output reg [3:0] recv_in__rdy;
	input wire [3:0] recv_in__val;
	input wire [137:0] recv_opt__msg;
	output reg [0:0] recv_opt__rdy;
	input wire [0:0] recv_opt__val;
	output reg [69:0] send_out__msg;
	input wire [1:0] send_out__rdy;
	output reg [1:0] send_out__val;
	output wire [8:0] to_mem_raddr__msg;
	input wire [2:0] to_mem_raddr__rdy;
	output wire [2:0] to_mem_raddr__val;
	output wire [8:0] to_mem_waddr__msg;
	input wire [2:0] to_mem_waddr__rdy;
	output wire [2:0] to_mem_waddr__val;
	output wire [104:0] to_mem_wdata__msg;
	input wire [2:0] to_mem_wdata__rdy;
	output wire [2:0] to_mem_wdata__val;
	localparam [1:0] __const__num_outports_at_comb_logic = 2'd2;
	localparam [2:0] __const__num_inports_at_comb_logic = 3'd4;
	reg [2:0] fu_recv_const_rdy_vector;
	reg [2:0] fu_recv_in_rdy_vector [0:3];
	reg [2:0] fu_recv_opt_rdy_vector;
	wire [0:0] fu__clk [0:2];
	wire [0:0] fu__reset [0:2];
	wire [34:0] fu__from_mem_rdata__msg [0:2];
	wire [0:0] fu__from_mem_rdata__rdy [0:2];
	wire [0:0] fu__from_mem_rdata__val [0:2];
	reg [34:0] fu__recv_const__msg [0:2];
	wire [0:0] fu__recv_const__rdy [0:2];
	reg [0:0] fu__recv_const__val [0:2];
	reg [139:0] fu__recv_in__msg [0:2];
	wire [3:0] fu__recv_in__rdy [0:2];
	reg [3:0] fu__recv_in__val [0:2];
	reg [137:0] fu__recv_opt__msg [0:2];
	wire [0:0] fu__recv_opt__rdy [0:2];
	reg [0:0] fu__recv_opt__val [0:2];
	wire [69:0] fu__send_out__msg [0:2];
	reg [1:0] fu__send_out__rdy [0:2];
	wire [1:0] fu__send_out__val [0:2];
	wire [2:0] fu__to_mem_raddr__msg [0:2];
	wire [0:0] fu__to_mem_raddr__rdy [0:2];
	wire [0:0] fu__to_mem_raddr__val [0:2];
	wire [2:0] fu__to_mem_waddr__msg [0:2];
	wire [0:0] fu__to_mem_waddr__rdy [0:2];
	wire [0:0] fu__to_mem_waddr__val [0:2];
	wire [34:0] fu__to_mem_wdata__msg [0:2];
	wire [0:0] fu__to_mem_wdata__rdy [0:2];
	wire [0:0] fu__to_mem_wdata__val [0:2];
	MemUnitRTL__a685aceb001a2483 fu__0(
		.clk(fu__clk[0]),
		.reset(fu__reset[0]),
		.from_mem_rdata__msg(fu__from_mem_rdata__msg[0]),
		.from_mem_rdata__rdy(fu__from_mem_rdata__rdy[0]),
		.from_mem_rdata__val(fu__from_mem_rdata__val[0]),
		.recv_const__msg(fu__recv_const__msg[0]),
		.recv_const__rdy(fu__recv_const__rdy[0]),
		.recv_const__val(fu__recv_const__val[0]),
		.recv_in__msg(fu__recv_in__msg[0]),
		.recv_in__rdy(fu__recv_in__rdy[0]),
		.recv_in__val(fu__recv_in__val[0]),
		.recv_opt__msg(fu__recv_opt__msg[0]),
		.recv_opt__rdy(fu__recv_opt__rdy[0]),
		.recv_opt__val(fu__recv_opt__val[0]),
		.send_out__msg(fu__send_out__msg[0]),
		.send_out__rdy(fu__send_out__rdy[0]),
		.send_out__val(fu__send_out__val[0]),
		.to_mem_raddr__msg(fu__to_mem_raddr__msg[0]),
		.to_mem_raddr__rdy(fu__to_mem_raddr__rdy[0]),
		.to_mem_raddr__val(fu__to_mem_raddr__val[0]),
		.to_mem_waddr__msg(fu__to_mem_waddr__msg[0]),
		.to_mem_waddr__rdy(fu__to_mem_waddr__rdy[0]),
		.to_mem_waddr__val(fu__to_mem_waddr__val[0]),
		.to_mem_wdata__msg(fu__to_mem_wdata__msg[0]),
		.to_mem_wdata__rdy(fu__to_mem_wdata__rdy[0]),
		.to_mem_wdata__val(fu__to_mem_wdata__val[0])
	);
	AdderRTL__a685aceb001a2483 fu__1(
		.clk(fu__clk[1]),
		.reset(fu__reset[1]),
		.from_mem_rdata__msg(fu__from_mem_rdata__msg[1]),
		.from_mem_rdata__rdy(fu__from_mem_rdata__rdy[1]),
		.from_mem_rdata__val(fu__from_mem_rdata__val[1]),
		.recv_const__msg(fu__recv_const__msg[1]),
		.recv_const__rdy(fu__recv_const__rdy[1]),
		.recv_const__val(fu__recv_const__val[1]),
		.recv_in__msg(fu__recv_in__msg[1]),
		.recv_in__rdy(fu__recv_in__rdy[1]),
		.recv_in__val(fu__recv_in__val[1]),
		.recv_opt__msg(fu__recv_opt__msg[1]),
		.recv_opt__rdy(fu__recv_opt__rdy[1]),
		.recv_opt__val(fu__recv_opt__val[1]),
		.send_out__msg(fu__send_out__msg[1]),
		.send_out__rdy(fu__send_out__rdy[1]),
		.send_out__val(fu__send_out__val[1]),
		.to_mem_raddr__msg(fu__to_mem_raddr__msg[1]),
		.to_mem_raddr__rdy(fu__to_mem_raddr__rdy[1]),
		.to_mem_raddr__val(fu__to_mem_raddr__val[1]),
		.to_mem_waddr__msg(fu__to_mem_waddr__msg[1]),
		.to_mem_waddr__rdy(fu__to_mem_waddr__rdy[1]),
		.to_mem_waddr__val(fu__to_mem_waddr__val[1]),
		.to_mem_wdata__msg(fu__to_mem_wdata__msg[1]),
		.to_mem_wdata__rdy(fu__to_mem_wdata__rdy[1]),
		.to_mem_wdata__val(fu__to_mem_wdata__val[1])
	);
	NahRTL__a685aceb001a2483 fu__2(
		.clk(fu__clk[2]),
		.reset(fu__reset[2]),
		.from_mem_rdata__msg(fu__from_mem_rdata__msg[2]),
		.from_mem_rdata__rdy(fu__from_mem_rdata__rdy[2]),
		.from_mem_rdata__val(fu__from_mem_rdata__val[2]),
		.recv_const__msg(fu__recv_const__msg[2]),
		.recv_const__rdy(fu__recv_const__rdy[2]),
		.recv_const__val(fu__recv_const__val[2]),
		.recv_in__msg(fu__recv_in__msg[2]),
		.recv_in__rdy(fu__recv_in__rdy[2]),
		.recv_in__val(fu__recv_in__val[2]),
		.recv_opt__msg(fu__recv_opt__msg[2]),
		.recv_opt__rdy(fu__recv_opt__rdy[2]),
		.recv_opt__val(fu__recv_opt__val[2]),
		.send_out__msg(fu__send_out__msg[2]),
		.send_out__rdy(fu__send_out__rdy[2]),
		.send_out__val(fu__send_out__val[2]),
		.to_mem_raddr__msg(fu__to_mem_raddr__msg[2]),
		.to_mem_raddr__rdy(fu__to_mem_raddr__rdy[2]),
		.to_mem_raddr__val(fu__to_mem_raddr__val[2]),
		.to_mem_waddr__msg(fu__to_mem_waddr__msg[2]),
		.to_mem_waddr__rdy(fu__to_mem_waddr__rdy[2]),
		.to_mem_waddr__val(fu__to_mem_waddr__val[2]),
		.to_mem_wdata__msg(fu__to_mem_wdata__msg[2]),
		.to_mem_wdata__rdy(fu__to_mem_wdata__rdy[2]),
		.to_mem_wdata__val(fu__to_mem_wdata__val[2])
	);
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : comb_logic
		begin : sv2v_autoblock_1
			reg [31:0] j;
			for (j = 1'd0; j < __const__num_outports_at_comb_logic; j = j + 1'd1)
				begin
					send_out__val[1 - sv2v_cast_1(j)+:1] = 1'd0;
					send_out__msg[(1 - sv2v_cast_1(j)) * 35+:35] = 35'h000000000;
				end
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < 2'd3; i = i + 1'd1)
				begin
					fu__recv_const__msg[sv2v_cast_2(i)] = recv_const__msg;
					fu__recv_const__val[sv2v_cast_2(i)] = recv_const__val;
					fu_recv_const_rdy_vector[sv2v_cast_2(i)] = fu__recv_const__rdy[sv2v_cast_2(i)];
					fu__recv_opt__msg[sv2v_cast_2(i)] = recv_opt__msg;
					fu__recv_opt__val[sv2v_cast_2(i)] = recv_opt__val;
					fu_recv_opt_rdy_vector[sv2v_cast_2(i)] = fu__recv_opt__rdy[sv2v_cast_2(i)];
					begin : sv2v_autoblock_3
						reg [31:0] j;
						for (j = 1'd0; j < __const__num_outports_at_comb_logic; j = j + 1'd1)
							begin
								if (fu__send_out__val[sv2v_cast_2(i)][1 - sv2v_cast_1(j)+:1]) begin
									send_out__msg[(1 - sv2v_cast_1(j)) * 35+:35] = fu__send_out__msg[sv2v_cast_2(i)][(1 - sv2v_cast_1(j)) * 35+:35];
									send_out__val[1 - sv2v_cast_1(j)+:1] = fu__send_out__val[sv2v_cast_2(i)][1 - sv2v_cast_1(j)+:1];
								end
								fu__send_out__rdy[sv2v_cast_2(i)][1 - sv2v_cast_1(j)+:1] = send_out__rdy[1 - sv2v_cast_1(j)+:1];
							end
					end
				end
		end
		recv_const__rdy = |fu_recv_const_rdy_vector;
		recv_opt__rdy = |fu_recv_opt_rdy_vector | (prologue_count_inport != 3'd0);
		begin : sv2v_autoblock_4
			reg [31:0] j;
			for (j = 1'd0; j < __const__num_inports_at_comb_logic; j = j + 1'd1)
				recv_in__rdy[3 - sv2v_cast_2(j)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_5
			reg [31:0] port;
			for (port = 1'd0; port < __const__num_inports_at_comb_logic; port = port + 1'd1)
				begin
					begin : sv2v_autoblock_6
						reg [31:0] i;
						for (i = 1'd0; i < 2'd3; i = i + 1'd1)
							begin
								fu__recv_in__msg[sv2v_cast_2(i)][(3 - sv2v_cast_2(port)) * 35+:35] = recv_in__msg[(3 - sv2v_cast_2(port)) * 35+:35];
								fu__recv_in__val[sv2v_cast_2(i)][3 - sv2v_cast_2(port)+:1] = recv_in__val[3 - sv2v_cast_2(port)+:1];
								fu_recv_in_rdy_vector[sv2v_cast_2(port)][sv2v_cast_2(i)] = fu__recv_in__rdy[sv2v_cast_2(i)][3 - sv2v_cast_2(port)+:1];
							end
					end
					recv_in__rdy[3 - sv2v_cast_2(port)+:1] = |fu_recv_in_rdy_vector[sv2v_cast_2(port)];
				end
		end
	end
	assign fu__clk[0] = clk;
	assign fu__reset[0] = reset;
	assign fu__clk[1] = clk;
	assign fu__reset[1] = reset;
	assign fu__clk[2] = clk;
	assign fu__reset[2] = reset;
	assign to_mem_raddr__msg[6+:3] = fu__to_mem_raddr__msg[0];
	assign fu__to_mem_raddr__rdy[0] = to_mem_raddr__rdy[2+:1];
	assign to_mem_raddr__val[2+:1] = fu__to_mem_raddr__val[0];
	assign fu__from_mem_rdata__msg[0] = from_mem_rdata__msg[70+:35];
	assign from_mem_rdata__rdy[2+:1] = fu__from_mem_rdata__rdy[0];
	assign fu__from_mem_rdata__val[0] = from_mem_rdata__val[2+:1];
	assign to_mem_waddr__msg[6+:3] = fu__to_mem_waddr__msg[0];
	assign fu__to_mem_waddr__rdy[0] = to_mem_waddr__rdy[2+:1];
	assign to_mem_waddr__val[2+:1] = fu__to_mem_waddr__val[0];
	assign to_mem_wdata__msg[70+:35] = fu__to_mem_wdata__msg[0];
	assign fu__to_mem_wdata__rdy[0] = to_mem_wdata__rdy[2+:1];
	assign to_mem_wdata__val[2+:1] = fu__to_mem_wdata__val[0];
	assign to_mem_raddr__msg[3+:3] = fu__to_mem_raddr__msg[1];
	assign fu__to_mem_raddr__rdy[1] = to_mem_raddr__rdy[1+:1];
	assign to_mem_raddr__val[1+:1] = fu__to_mem_raddr__val[1];
	assign fu__from_mem_rdata__msg[1] = from_mem_rdata__msg[35+:35];
	assign from_mem_rdata__rdy[1+:1] = fu__from_mem_rdata__rdy[1];
	assign fu__from_mem_rdata__val[1] = from_mem_rdata__val[1+:1];
	assign to_mem_waddr__msg[3+:3] = fu__to_mem_waddr__msg[1];
	assign fu__to_mem_waddr__rdy[1] = to_mem_waddr__rdy[1+:1];
	assign to_mem_waddr__val[1+:1] = fu__to_mem_waddr__val[1];
	assign to_mem_wdata__msg[35+:35] = fu__to_mem_wdata__msg[1];
	assign fu__to_mem_wdata__rdy[1] = to_mem_wdata__rdy[1+:1];
	assign to_mem_wdata__val[1+:1] = fu__to_mem_wdata__val[1];
	assign to_mem_raddr__msg[0+:3] = fu__to_mem_raddr__msg[2];
	assign fu__to_mem_raddr__rdy[2] = to_mem_raddr__rdy[0+:1];
	assign to_mem_raddr__val[0+:1] = fu__to_mem_raddr__val[2];
	assign fu__from_mem_rdata__msg[2] = from_mem_rdata__msg[0+:35];
	assign from_mem_rdata__rdy[0+:1] = fu__from_mem_rdata__rdy[2];
	assign fu__from_mem_rdata__val[2] = from_mem_rdata__val[0+:1];
	assign to_mem_waddr__msg[0+:3] = fu__to_mem_waddr__msg[2];
	assign fu__to_mem_waddr__rdy[2] = to_mem_waddr__rdy[0+:1];
	assign to_mem_waddr__val[0+:1] = fu__to_mem_waddr__val[2];
	assign to_mem_wdata__msg[0+:35] = fu__to_mem_wdata__msg[2];
	assign fu__to_mem_wdata__rdy[2] = to_mem_wdata__rdy[0+:1];
	assign to_mem_wdata__val[0+:1] = fu__to_mem_wdata__val[2];
endmodule
module CrossbarRTL__542f2f2c623caccb (
	clk,
	compute_done,
	crossbar_id,
	crossbar_outport,
	ctrl_addr_inport,
	prologue_count_inport,
	reset,
	tile_id,
	recv_data__msg,
	recv_data__rdy,
	recv_data__val,
	recv_opt__msg,
	recv_opt__rdy,
	recv_opt__val,
	send_data__msg,
	send_data__rdy,
	send_data__val
);
	input wire [0:0] clk;
	input wire [0:0] compute_done;
	input wire [0:0] crossbar_id;
	input wire [23:0] crossbar_outport;
	input wire [2:0] ctrl_addr_inport;
	input wire [35:0] prologue_count_inport;
	input wire [0:0] reset;
	input wire [2:0] tile_id;
	input wire [69:0] recv_data__msg;
	output reg [1:0] recv_data__rdy;
	input wire [1:0] recv_data__val;
	input wire [137:0] recv_opt__msg;
	output reg [0:0] recv_opt__rdy;
	input wire [0:0] recv_opt__val;
	output reg [419:0] send_data__msg;
	input wire [11:0] send_data__rdy;
	output reg [11:0] send_data__val;
	localparam [1:0] __const__num_inports_at_update_signal = 2'd2;
	localparam [3:0] __const__num_outports_at_update_signal = 4'd12;
	localparam [5:0] __const__OPT_START = 6'd0;
	localparam [2:0] __const__ctrl_mem_size_at_update_prologue_counter = 3'd6;
	localparam [1:0] __const__num_inports_at_update_prologue_counter = 2'd2;
	localparam [2:0] __const__ctrl_mem_size_at_update_prologue_counter_next = 3'd6;
	localparam [1:0] __const__num_inports_at_update_prologue_counter_next = 2'd2;
	localparam [3:0] __const__num_outports_at_update_prologue_counter_next = 4'd12;
	localparam [3:0] __const__num_outports_at_update_prologue_allowing_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_prologue_or_valid_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_in_dir_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_rdy_vector = 4'd12;
	localparam [3:0] __const__outport_towards_local_base_id_at_update_rdy_vector = 4'd8;
	localparam [3:0] __const__num_outports_at_update_valid_vector = 4'd12;
	localparam [1:0] __const__num_inports_at_update_recv_required_vector = 2'd2;
	localparam [3:0] __const__num_outports_at_update_recv_required_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_send_required_vector = 4'd12;
	reg [1:0] in_dir [0:11];
	reg [0:0] in_dir_local [0:11];
	reg [11:0] prologue_allowing_vector;
	wire [2:0] prologue_count_wire [0:5][0:1];
	reg [2:0] prologue_counter [0:5][0:1];
	reg [2:0] prologue_counter_next [0:5][0:1];
	wire [34:0] recv_data_msg [0:1];
	wire [0:0] recv_data_val [0:1];
	reg [1:0] recv_required_vector;
	reg [11:0] recv_valid_or_prologue_allowing_vector;
	reg [11:0] recv_valid_vector;
	reg [11:0] send_rdy_vector;
	reg [11:0] send_required_vector;
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : update_in_dir_vector
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_in_dir_vector; i = i + 1'd1)
				begin
					in_dir[sv2v_cast_4(i)] = 2'd0;
					in_dir_local[sv2v_cast_4(i)] = 1'd0;
				end
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_in_dir_vector; i = i + 1'd1)
				begin
					in_dir[sv2v_cast_4(i)] = crossbar_outport[(11 - sv2v_cast_4(i)) * 2+:2];
					if (in_dir[sv2v_cast_4(i)] > 2'd0)
						in_dir_local[sv2v_cast_4(i)] = sv2v_cast_1(in_dir[sv2v_cast_4(i)] - 2'd1);
				end
		end
	end
	always @(*) begin : update_prologue_allowing_vector
		prologue_allowing_vector = 12'd0;
		begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_prologue_allowing_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 2'd0)
					prologue_allowing_vector[sv2v_cast_4(i)] = prologue_counter[ctrl_addr_inport][in_dir_local[sv2v_cast_4(i)]] < prologue_count_wire[ctrl_addr_inport][in_dir_local[sv2v_cast_4(i)]];
				else
					prologue_allowing_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : update_prologue_counter_next
		begin : sv2v_autoblock_4
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_counter_next; addr = addr + 1'd1)
				begin : sv2v_autoblock_5
					reg [31:0] i;
					for (i = 1'd0; i < __const__num_inports_at_update_prologue_counter_next; i = i + 1'd1)
						begin
							prologue_counter_next[sv2v_cast_3(addr)][sv2v_cast_1(i)] = prologue_counter[sv2v_cast_3(addr)][sv2v_cast_1(i)];
							begin : sv2v_autoblock_6
								reg [31:0] j;
								for (j = 1'd0; j < __const__num_outports_at_update_prologue_counter_next; j = j + 1'd1)
									if ((((recv_opt__rdy & (in_dir[sv2v_cast_4(j)] > 2'd0)) & (in_dir_local[sv2v_cast_4(j)] == sv2v_cast_1(i))) & (sv2v_cast_3(addr) == ctrl_addr_inport)) & (prologue_counter[sv2v_cast_3(addr)][sv2v_cast_1(i)] < prologue_count_wire[sv2v_cast_3(addr)][sv2v_cast_1(i)]))
										prologue_counter_next[sv2v_cast_3(addr)][sv2v_cast_1(i)] = prologue_counter[sv2v_cast_3(addr)][sv2v_cast_1(i)] + 3'd1;
							end
						end
				end
		end
	end
	always @(*) begin : update_prologue_or_valid_vector
		recv_valid_or_prologue_allowing_vector = 12'd0;
		begin : sv2v_autoblock_7
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_prologue_or_valid_vector; i = i + 1'd1)
				recv_valid_or_prologue_allowing_vector[sv2v_cast_4(i)] = recv_valid_vector[sv2v_cast_4(i)] | prologue_allowing_vector[sv2v_cast_4(i)];
		end
	end
	always @(*) begin : update_rdy_vector
		send_rdy_vector = 12'd0;
		begin : sv2v_autoblock_8
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_rdy_vector; i = i + 1'd1)
				if ((in_dir[sv2v_cast_4(i)] > 2'd0) & (~compute_done | (sv2v_cast_4(i) < __const__outport_towards_local_base_id_at_update_rdy_vector)))
					send_rdy_vector[sv2v_cast_4(i)] = send_data__rdy[11 - sv2v_cast_4(i)+:1];
				else
					send_rdy_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(*) begin : update_recv_required_vector
		begin : sv2v_autoblock_9
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_update_recv_required_vector; i = i + 1'd1)
				recv_required_vector[sv2v_cast_1(i)] = 1'd0;
		end
		begin : sv2v_autoblock_10
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_recv_required_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 2'd0)
					recv_required_vector[in_dir_local[sv2v_cast_4(i)]] = 1'd1;
		end
	end
	always @(*) begin : update_send_required_vector
		begin : sv2v_autoblock_11
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_send_required_vector; i = i + 1'd1)
				send_required_vector[sv2v_cast_4(i)] = 1'd0;
		end
		begin : sv2v_autoblock_12
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_send_required_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 2'd0)
					send_required_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(*) begin : update_signal
		begin : sv2v_autoblock_13
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_update_signal; i = i + 1'd1)
				recv_data__rdy[1 - sv2v_cast_1(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_14
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_signal; i = i + 1'd1)
				begin
					send_data__val[11 - sv2v_cast_4(i)+:1] = 1'd0;
					send_data__msg[(11 - sv2v_cast_4(i)) * 35+:35] = 35'h000000000;
				end
		end
		recv_opt__rdy = 1'd0;
		if (recv_opt__val & (recv_opt__msg[137-:6] != __const__OPT_START)) begin
			begin : sv2v_autoblock_15
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_inports_at_update_signal; i = i + 1'd1)
					recv_data__rdy[1 - sv2v_cast_1(i)+:1] = (&recv_valid_vector & &send_rdy_vector) & recv_required_vector[sv2v_cast_1(i)];
			end
			begin : sv2v_autoblock_16
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_outports_at_update_signal; i = i + 1'd1)
					begin
						send_data__val[11 - sv2v_cast_4(i)+:1] = &recv_valid_vector & send_required_vector[sv2v_cast_4(i)];
						if (&recv_valid_vector & send_required_vector[sv2v_cast_4(i)]) begin
							send_data__msg[((11 - sv2v_cast_4(i)) * 35) + 34-:32] = recv_data_msg[in_dir_local[sv2v_cast_4(i)]][34-:32];
							send_data__msg[((11 - sv2v_cast_4(i)) * 35) + 2] = recv_data_msg[in_dir_local[sv2v_cast_4(i)]][2];
						end
					end
			end
			recv_opt__rdy = &send_rdy_vector & &recv_valid_or_prologue_allowing_vector;
		end
	end
	always @(*) begin : update_valid_vector
		recv_valid_vector = 12'd0;
		begin : sv2v_autoblock_17
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_valid_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 2'd0)
					recv_valid_vector[sv2v_cast_4(i)] = recv_data_val[in_dir_local[sv2v_cast_4(i)]];
				else
					recv_valid_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(posedge clk) begin : update_prologue_counter
		if (reset) begin : sv2v_autoblock_18
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_counter; addr = addr + 1'd1)
				begin : sv2v_autoblock_19
					reg [31:0] i;
					for (i = 1'd0; i < __const__num_inports_at_update_prologue_counter; i = i + 1'd1)
						prologue_counter[sv2v_cast_3(addr)][sv2v_cast_1(i)] <= 3'd0;
				end
		end
		else begin : sv2v_autoblock_20
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_counter; addr = addr + 1'd1)
				begin : sv2v_autoblock_21
					reg [31:0] i;
					for (i = 1'd0; i < __const__num_inports_at_update_prologue_counter; i = i + 1'd1)
						prologue_counter[sv2v_cast_3(addr)][sv2v_cast_1(i)] <= prologue_counter_next[sv2v_cast_3(addr)][sv2v_cast_1(i)];
				end
		end
	end
	assign recv_data_msg[0] = recv_data__msg[35+:35];
	assign recv_data_val[0] = recv_data__val[1+:1];
	assign recv_data_msg[1] = recv_data__msg[0+:35];
	assign recv_data_val[1] = recv_data__val[0+:1];
	assign prologue_count_wire[0][0] = prologue_count_inport[33+:3];
	assign prologue_count_wire[0][1] = prologue_count_inport[30+:3];
	assign prologue_count_wire[1][0] = prologue_count_inport[27+:3];
	assign prologue_count_wire[1][1] = prologue_count_inport[24+:3];
	assign prologue_count_wire[2][0] = prologue_count_inport[21+:3];
	assign prologue_count_wire[2][1] = prologue_count_inport[18+:3];
	assign prologue_count_wire[3][0] = prologue_count_inport[15+:3];
	assign prologue_count_wire[3][1] = prologue_count_inport[12+:3];
	assign prologue_count_wire[4][0] = prologue_count_inport[9+:3];
	assign prologue_count_wire[4][1] = prologue_count_inport[6+:3];
	assign prologue_count_wire[5][0] = prologue_count_inport[3+:3];
	assign prologue_count_wire[5][1] = prologue_count_inport[0+:3];
endmodule
module RegisterFile__84f0703fd9bfd535 (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [3:0] raddr;
	output reg [34:0] rdata;
	input wire [0:0] reset;
	input wire [3:0] waddr;
	input wire [34:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [34:0] regs [0:15];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 35+:35] = regs[raddr[sv2v_cast_1(i) * 4+:4]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i) * 4+:4]] <= wdata[sv2v_cast_1(i) * 35+:35];
		end
	end
endmodule
module RegisterBankRTL__0403a2cf39272350 (
	clk,
	inport_opt,
	inport_valid,
	inport_wdata,
	reset,
	send_data_to_fu__msg,
	send_data_to_fu__rdy,
	send_data_to_fu__val
);
	input wire [0:0] clk;
	input wire [137:0] inport_opt;
	input wire [2:0] inport_valid;
	input wire [104:0] inport_wdata;
	input wire [0:0] reset;
	output reg [34:0] send_data_to_fu__msg;
	input wire [0:0] send_data_to_fu__rdy;
	output reg [0:0] send_data_to_fu__val;
	localparam [0:0] __const__reg_bank_id_at_access_registers = 1'd0;
	localparam [0:0] __const__reg_bank_id_at_update_send_val = 1'd0;
	wire [0:0] reg_file__clk;
	reg [3:0] reg_file__raddr;
	wire [34:0] reg_file__rdata;
	wire [0:0] reg_file__reset;
	reg [3:0] reg_file__waddr;
	reg [34:0] reg_file__wdata;
	reg [0:0] reg_file__wen;
	RegisterFile__84f0703fd9bfd535 reg_file(
		.clk(reg_file__clk),
		.raddr(reg_file__raddr),
		.rdata(reg_file__rdata),
		.reset(reg_file__reset),
		.waddr(reg_file__waddr),
		.wdata(reg_file__wdata),
		.wen(reg_file__wen)
	);
	reg [1:0] __tmpvar__access_registers_write_reg_from;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : access_registers
		reg_file__raddr[1'd0 * 4+:4] = 4'd0;
		send_data_to_fu__msg = 35'h000000000;
		reg_file__waddr[1'd0 * 4+:4] = 4'd0;
		reg_file__wdata[1'd0 * 35+:35] = 35'h000000000;
		reg_file__wen[1'd0+:1] = 1'd0;
		if (inport_opt[16 + sv2v_cast_2(__const__reg_bank_id_at_access_registers)+:1]) begin
			reg_file__raddr[1'd0 * 4+:4] = inport_opt[0 + (sv2v_cast_2(__const__reg_bank_id_at_access_registers) * 4)+:4];
			send_data_to_fu__msg = reg_file__rdata[1'd0 * 35+:35];
		end
		__tmpvar__access_registers_write_reg_from = inport_opt[36 + (sv2v_cast_2(__const__reg_bank_id_at_access_registers) * 2)+:2];
		if (~reset & (__tmpvar__access_registers_write_reg_from > 2'd0))
			if (inport_valid[(2 + 2'd1) - __tmpvar__access_registers_write_reg_from+:1]) begin
				reg_file__waddr[1'd0 * 4+:4] = inport_opt[20 + (sv2v_cast_2(__const__reg_bank_id_at_access_registers) * 4)+:4];
				reg_file__wdata[1'd0 * 35+:35] = inport_wdata[((2 + 2'd1) - __tmpvar__access_registers_write_reg_from) * 35+:35];
				reg_file__wen[1'd0+:1] = 1'd1;
			end
	end
	always @(*) begin : update_send_val
		send_data_to_fu__val = 1'd0;
		if (~reset & inport_opt[16 + sv2v_cast_2(__const__reg_bank_id_at_update_send_val)+:1])
			send_data_to_fu__val = 1'd1;
	end
	assign reg_file__clk = clk;
	assign reg_file__reset = reset;
endmodule
module RegisterBankRTL__46c92e34749cd06f (
	clk,
	inport_opt,
	inport_valid,
	inport_wdata,
	reset,
	send_data_to_fu__msg,
	send_data_to_fu__rdy,
	send_data_to_fu__val
);
	input wire [0:0] clk;
	input wire [137:0] inport_opt;
	input wire [2:0] inport_valid;
	input wire [104:0] inport_wdata;
	input wire [0:0] reset;
	output reg [34:0] send_data_to_fu__msg;
	input wire [0:0] send_data_to_fu__rdy;
	output reg [0:0] send_data_to_fu__val;
	localparam [0:0] __const__reg_bank_id_at_access_registers = 1'd1;
	localparam [0:0] __const__reg_bank_id_at_update_send_val = 1'd1;
	wire [0:0] reg_file__clk;
	reg [3:0] reg_file__raddr;
	wire [34:0] reg_file__rdata;
	wire [0:0] reg_file__reset;
	reg [3:0] reg_file__waddr;
	reg [34:0] reg_file__wdata;
	reg [0:0] reg_file__wen;
	RegisterFile__84f0703fd9bfd535 reg_file(
		.clk(reg_file__clk),
		.raddr(reg_file__raddr),
		.rdata(reg_file__rdata),
		.reset(reg_file__reset),
		.waddr(reg_file__waddr),
		.wdata(reg_file__wdata),
		.wen(reg_file__wen)
	);
	reg [1:0] __tmpvar__access_registers_write_reg_from;
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : access_registers
		reg_file__raddr[1'd0 * 4+:4] = 4'd0;
		send_data_to_fu__msg = 35'h000000000;
		reg_file__waddr[1'd0 * 4+:4] = 4'd0;
		reg_file__wdata[1'd0 * 35+:35] = 35'h000000000;
		reg_file__wen[1'd0+:1] = 1'd0;
		if (inport_opt[16 + sv2v_cast_2(__const__reg_bank_id_at_access_registers)+:1]) begin
			reg_file__raddr[1'd0 * 4+:4] = inport_opt[0 + (sv2v_cast_2(__const__reg_bank_id_at_access_registers) * 4)+:4];
			send_data_to_fu__msg = reg_file__rdata[1'd0 * 35+:35];
		end
		__tmpvar__access_registers_write_reg_from = inport_opt[36 + (sv2v_cast_2(__const__reg_bank_id_at_access_registers) * 2)+:2];
		if (~reset & (__tmpvar__access_registers_write_reg_from > 2'd0))
			if (inport_valid[(2 + 2'd1) - __tmpvar__access_registers_write_reg_from+:1]) begin
				reg_file__waddr[1'd0 * 4+:4] = inport_opt[20 + (sv2v_cast_2(__const__reg_bank_id_at_access_registers) * 4)+:4];
				reg_file__wdata[1'd0 * 35+:35] = inport_wdata[((2 + 2'd1) - __tmpvar__access_registers_write_reg_from) * 35+:35];
				reg_file__wen[1'd0+:1] = 1'd1;
			end
	end
	always @(*) begin : update_send_val
		send_data_to_fu__val = 1'd0;
		if (~reset & inport_opt[16 + sv2v_cast_2(__const__reg_bank_id_at_update_send_val)+:1])
			send_data_to_fu__val = 1'd1;
	end
	assign reg_file__clk = clk;
	assign reg_file__reset = reset;
endmodule
module RegisterBankRTL__399b6fb493c59ea1 (
	clk,
	inport_opt,
	inport_valid,
	inport_wdata,
	reset,
	send_data_to_fu__msg,
	send_data_to_fu__rdy,
	send_data_to_fu__val
);
	input wire [0:0] clk;
	input wire [137:0] inport_opt;
	input wire [2:0] inport_valid;
	input wire [104:0] inport_wdata;
	input wire [0:0] reset;
	output reg [34:0] send_data_to_fu__msg;
	input wire [0:0] send_data_to_fu__rdy;
	output reg [0:0] send_data_to_fu__val;
	localparam [1:0] __const__reg_bank_id_at_access_registers = 2'd2;
	localparam [1:0] __const__reg_bank_id_at_update_send_val = 2'd2;
	wire [0:0] reg_file__clk;
	reg [3:0] reg_file__raddr;
	wire [34:0] reg_file__rdata;
	wire [0:0] reg_file__reset;
	reg [3:0] reg_file__waddr;
	reg [34:0] reg_file__wdata;
	reg [0:0] reg_file__wen;
	RegisterFile__84f0703fd9bfd535 reg_file(
		.clk(reg_file__clk),
		.raddr(reg_file__raddr),
		.rdata(reg_file__rdata),
		.reset(reg_file__reset),
		.waddr(reg_file__waddr),
		.wdata(reg_file__wdata),
		.wen(reg_file__wen)
	);
	reg [1:0] __tmpvar__access_registers_write_reg_from;
	always @(*) begin : access_registers
		reg_file__raddr[1'd0 * 4+:4] = 4'd0;
		send_data_to_fu__msg = 35'h000000000;
		reg_file__waddr[1'd0 * 4+:4] = 4'd0;
		reg_file__wdata[1'd0 * 35+:35] = 35'h000000000;
		reg_file__wen[1'd0+:1] = 1'd0;
		if (inport_opt[16 + __const__reg_bank_id_at_access_registers+:1]) begin
			reg_file__raddr[1'd0 * 4+:4] = inport_opt[0 + (__const__reg_bank_id_at_access_registers * 4)+:4];
			send_data_to_fu__msg = reg_file__rdata[1'd0 * 35+:35];
		end
		__tmpvar__access_registers_write_reg_from = inport_opt[36 + (__const__reg_bank_id_at_access_registers * 2)+:2];
		if (~reset & (__tmpvar__access_registers_write_reg_from > 2'd0))
			if (inport_valid[(2 + 2'd1) - __tmpvar__access_registers_write_reg_from+:1]) begin
				reg_file__waddr[1'd0 * 4+:4] = inport_opt[20 + (__const__reg_bank_id_at_access_registers * 4)+:4];
				reg_file__wdata[1'd0 * 35+:35] = inport_wdata[((2 + 2'd1) - __tmpvar__access_registers_write_reg_from) * 35+:35];
				reg_file__wen[1'd0+:1] = 1'd1;
			end
	end
	always @(*) begin : update_send_val
		send_data_to_fu__val = 1'd0;
		if (~reset & inport_opt[16 + __const__reg_bank_id_at_update_send_val+:1])
			send_data_to_fu__val = 1'd1;
	end
	assign reg_file__clk = clk;
	assign reg_file__reset = reset;
endmodule
module RegisterBankRTL__2e3bc73d72bd2e83 (
	clk,
	inport_opt,
	inport_valid,
	inport_wdata,
	reset,
	send_data_to_fu__msg,
	send_data_to_fu__rdy,
	send_data_to_fu__val
);
	input wire [0:0] clk;
	input wire [137:0] inport_opt;
	input wire [2:0] inport_valid;
	input wire [104:0] inport_wdata;
	input wire [0:0] reset;
	output reg [34:0] send_data_to_fu__msg;
	input wire [0:0] send_data_to_fu__rdy;
	output reg [0:0] send_data_to_fu__val;
	localparam [1:0] __const__reg_bank_id_at_access_registers = 2'd3;
	localparam [1:0] __const__reg_bank_id_at_update_send_val = 2'd3;
	wire [0:0] reg_file__clk;
	reg [3:0] reg_file__raddr;
	wire [34:0] reg_file__rdata;
	wire [0:0] reg_file__reset;
	reg [3:0] reg_file__waddr;
	reg [34:0] reg_file__wdata;
	reg [0:0] reg_file__wen;
	RegisterFile__84f0703fd9bfd535 reg_file(
		.clk(reg_file__clk),
		.raddr(reg_file__raddr),
		.rdata(reg_file__rdata),
		.reset(reg_file__reset),
		.waddr(reg_file__waddr),
		.wdata(reg_file__wdata),
		.wen(reg_file__wen)
	);
	reg [1:0] __tmpvar__access_registers_write_reg_from;
	always @(*) begin : access_registers
		reg_file__raddr[1'd0 * 4+:4] = 4'd0;
		send_data_to_fu__msg = 35'h000000000;
		reg_file__waddr[1'd0 * 4+:4] = 4'd0;
		reg_file__wdata[1'd0 * 35+:35] = 35'h000000000;
		reg_file__wen[1'd0+:1] = 1'd0;
		if (inport_opt[16 + __const__reg_bank_id_at_access_registers+:1]) begin
			reg_file__raddr[1'd0 * 4+:4] = inport_opt[0 + (__const__reg_bank_id_at_access_registers * 4)+:4];
			send_data_to_fu__msg = reg_file__rdata[1'd0 * 35+:35];
		end
		__tmpvar__access_registers_write_reg_from = inport_opt[36 + (__const__reg_bank_id_at_access_registers * 2)+:2];
		if (~reset & (__tmpvar__access_registers_write_reg_from > 2'd0))
			if (inport_valid[(2 + 2'd1) - __tmpvar__access_registers_write_reg_from+:1]) begin
				reg_file__waddr[1'd0 * 4+:4] = inport_opt[20 + (__const__reg_bank_id_at_access_registers * 4)+:4];
				reg_file__wdata[1'd0 * 35+:35] = inport_wdata[((2 + 2'd1) - __tmpvar__access_registers_write_reg_from) * 35+:35];
				reg_file__wen[1'd0+:1] = 1'd1;
			end
	end
	always @(*) begin : update_send_val
		send_data_to_fu__val = 1'd0;
		if (~reset & inport_opt[16 + __const__reg_bank_id_at_update_send_val+:1])
			send_data_to_fu__val = 1'd1;
	end
	assign reg_file__clk = clk;
	assign reg_file__reset = reset;
endmodule
module RegisterClusterRTL__a8b6c64c450b5f1b (
	clk,
	inport_opt,
	reset,
	recv_data_from_const__msg,
	recv_data_from_const__rdy,
	recv_data_from_const__val,
	recv_data_from_fu_crossbar__msg,
	recv_data_from_fu_crossbar__rdy,
	recv_data_from_fu_crossbar__val,
	recv_data_from_routing_crossbar__msg,
	recv_data_from_routing_crossbar__rdy,
	recv_data_from_routing_crossbar__val,
	send_data_to_fu__msg,
	send_data_to_fu__rdy,
	send_data_to_fu__val
);
	input wire [0:0] clk;
	input wire [137:0] inport_opt;
	input wire [0:0] reset;
	input wire [139:0] recv_data_from_const__msg;
	output reg [3:0] recv_data_from_const__rdy;
	input wire [3:0] recv_data_from_const__val;
	input wire [139:0] recv_data_from_fu_crossbar__msg;
	output reg [3:0] recv_data_from_fu_crossbar__rdy;
	input wire [3:0] recv_data_from_fu_crossbar__val;
	input wire [139:0] recv_data_from_routing_crossbar__msg;
	output reg [3:0] recv_data_from_routing_crossbar__rdy;
	input wire [3:0] recv_data_from_routing_crossbar__val;
	output reg [139:0] send_data_to_fu__msg;
	input wire [3:0] send_data_to_fu__rdy;
	output reg [3:0] send_data_to_fu__val;
	localparam [2:0] __const__num_reg_banks_at_update_msgs_signals = 3'd4;
	wire [0:0] reg_bank__clk [0:3];
	wire [137:0] reg_bank__inport_opt [0:3];
	wire [2:0] reg_bank__inport_valid [0:3];
	wire [104:0] reg_bank__inport_wdata [0:3];
	wire [0:0] reg_bank__reset [0:3];
	wire [34:0] reg_bank__send_data_to_fu__msg [0:3];
	reg [0:0] reg_bank__send_data_to_fu__rdy [0:3];
	wire [0:0] reg_bank__send_data_to_fu__val [0:3];
	RegisterBankRTL__0403a2cf39272350 reg_bank__0(
		.clk(reg_bank__clk[0]),
		.inport_opt(reg_bank__inport_opt[0]),
		.inport_valid(reg_bank__inport_valid[0]),
		.inport_wdata(reg_bank__inport_wdata[0]),
		.reset(reg_bank__reset[0]),
		.send_data_to_fu__msg(reg_bank__send_data_to_fu__msg[0]),
		.send_data_to_fu__rdy(reg_bank__send_data_to_fu__rdy[0]),
		.send_data_to_fu__val(reg_bank__send_data_to_fu__val[0])
	);
	RegisterBankRTL__46c92e34749cd06f reg_bank__1(
		.clk(reg_bank__clk[1]),
		.inport_opt(reg_bank__inport_opt[1]),
		.inport_valid(reg_bank__inport_valid[1]),
		.inport_wdata(reg_bank__inport_wdata[1]),
		.reset(reg_bank__reset[1]),
		.send_data_to_fu__msg(reg_bank__send_data_to_fu__msg[1]),
		.send_data_to_fu__rdy(reg_bank__send_data_to_fu__rdy[1]),
		.send_data_to_fu__val(reg_bank__send_data_to_fu__val[1])
	);
	RegisterBankRTL__399b6fb493c59ea1 reg_bank__2(
		.clk(reg_bank__clk[2]),
		.inport_opt(reg_bank__inport_opt[2]),
		.inport_valid(reg_bank__inport_valid[2]),
		.inport_wdata(reg_bank__inport_wdata[2]),
		.reset(reg_bank__reset[2]),
		.send_data_to_fu__msg(reg_bank__send_data_to_fu__msg[2]),
		.send_data_to_fu__rdy(reg_bank__send_data_to_fu__rdy[2]),
		.send_data_to_fu__val(reg_bank__send_data_to_fu__val[2])
	);
	RegisterBankRTL__2e3bc73d72bd2e83 reg_bank__3(
		.clk(reg_bank__clk[3]),
		.inport_opt(reg_bank__inport_opt[3]),
		.inport_valid(reg_bank__inport_valid[3]),
		.inport_wdata(reg_bank__inport_wdata[3]),
		.reset(reg_bank__reset[3]),
		.send_data_to_fu__msg(reg_bank__send_data_to_fu__msg[3]),
		.send_data_to_fu__rdy(reg_bank__send_data_to_fu__rdy[3]),
		.send_data_to_fu__val(reg_bank__send_data_to_fu__val[3])
	);
	function automatic [1:0] sv2v_cast_2;
		input reg [1:0] inp;
		sv2v_cast_2 = inp;
	endfunction
	always @(*) begin : update_msgs_signals
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_reg_banks_at_update_msgs_signals; i = i + 1'd1)
				begin
					send_data_to_fu__msg[(3 - sv2v_cast_2(i)) * 35+:35] = 35'h000000000;
					recv_data_from_routing_crossbar__rdy[3 - sv2v_cast_2(i)+:1] = 1'd0;
					recv_data_from_fu_crossbar__rdy[3 - sv2v_cast_2(i)+:1] = 1'd0;
					recv_data_from_const__rdy[3 - sv2v_cast_2(i)+:1] = 1'd0;
					send_data_to_fu__val[3 - sv2v_cast_2(i)+:1] = 1'd0;
				end
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_reg_banks_at_update_msgs_signals; i = i + 1'd1)
				begin
					if (recv_data_from_routing_crossbar__val[3 - sv2v_cast_2(i)+:1])
						send_data_to_fu__msg[(3 - sv2v_cast_2(i)) * 35+:35] = recv_data_from_routing_crossbar__msg[(3 - sv2v_cast_2(i)) * 35+:35];
					else
						send_data_to_fu__msg[(3 - sv2v_cast_2(i)) * 35+:35] = reg_bank__send_data_to_fu__msg[sv2v_cast_2(i)];
					send_data_to_fu__val[3 - sv2v_cast_2(i)+:1] = recv_data_from_routing_crossbar__val[3 - sv2v_cast_2(i)+:1] | reg_bank__send_data_to_fu__val[sv2v_cast_2(i)];
					reg_bank__send_data_to_fu__rdy[sv2v_cast_2(i)] = send_data_to_fu__rdy[3 - sv2v_cast_2(i)+:1];
					recv_data_from_routing_crossbar__rdy[3 - sv2v_cast_2(i)+:1] = send_data_to_fu__rdy[3 - sv2v_cast_2(i)+:1];
					recv_data_from_fu_crossbar__rdy[3 - sv2v_cast_2(i)+:1] = 1'd1;
					recv_data_from_const__rdy[3 - sv2v_cast_2(i)+:1] = 1'd1;
				end
		end
	end
	assign reg_bank__clk[0] = clk;
	assign reg_bank__reset[0] = reset;
	assign reg_bank__clk[1] = clk;
	assign reg_bank__reset[1] = reset;
	assign reg_bank__clk[2] = clk;
	assign reg_bank__reset[2] = reset;
	assign reg_bank__clk[3] = clk;
	assign reg_bank__reset[3] = reset;
	assign reg_bank__inport_opt[0] = inport_opt;
	assign reg_bank__inport_wdata[0][70+:35] = recv_data_from_routing_crossbar__msg[105+:35];
	assign reg_bank__inport_wdata[0][35+:35] = recv_data_from_fu_crossbar__msg[105+:35];
	assign reg_bank__inport_wdata[0][0+:35] = recv_data_from_const__msg[105+:35];
	assign reg_bank__inport_valid[0][2+:1] = recv_data_from_routing_crossbar__val[3+:1];
	assign reg_bank__inport_valid[0][1+:1] = recv_data_from_fu_crossbar__val[3+:1];
	assign reg_bank__inport_valid[0][0+:1] = recv_data_from_const__val[3+:1];
	assign reg_bank__inport_opt[1] = inport_opt;
	assign reg_bank__inport_wdata[1][70+:35] = recv_data_from_routing_crossbar__msg[70+:35];
	assign reg_bank__inport_wdata[1][35+:35] = recv_data_from_fu_crossbar__msg[70+:35];
	assign reg_bank__inport_wdata[1][0+:35] = recv_data_from_const__msg[70+:35];
	assign reg_bank__inport_valid[1][2+:1] = recv_data_from_routing_crossbar__val[2+:1];
	assign reg_bank__inport_valid[1][1+:1] = recv_data_from_fu_crossbar__val[2+:1];
	assign reg_bank__inport_valid[1][0+:1] = recv_data_from_const__val[2+:1];
	assign reg_bank__inport_opt[2] = inport_opt;
	assign reg_bank__inport_wdata[2][70+:35] = recv_data_from_routing_crossbar__msg[35+:35];
	assign reg_bank__inport_wdata[2][35+:35] = recv_data_from_fu_crossbar__msg[35+:35];
	assign reg_bank__inport_wdata[2][0+:35] = recv_data_from_const__msg[35+:35];
	assign reg_bank__inport_valid[2][2+:1] = recv_data_from_routing_crossbar__val[1+:1];
	assign reg_bank__inport_valid[2][1+:1] = recv_data_from_fu_crossbar__val[1+:1];
	assign reg_bank__inport_valid[2][0+:1] = recv_data_from_const__val[1+:1];
	assign reg_bank__inport_opt[3] = inport_opt;
	assign reg_bank__inport_wdata[3][70+:35] = recv_data_from_routing_crossbar__msg[0+:35];
	assign reg_bank__inport_wdata[3][35+:35] = recv_data_from_fu_crossbar__msg[0+:35];
	assign reg_bank__inport_wdata[3][0+:35] = recv_data_from_const__msg[0+:35];
	assign reg_bank__inport_valid[3][2+:1] = recv_data_from_routing_crossbar__val[0+:1];
	assign reg_bank__inport_valid[3][1+:1] = recv_data_from_fu_crossbar__val[0+:1];
	assign reg_bank__inport_valid[3][0+:1] = recv_data_from_const__val[0+:1];
endmodule
module CrossbarRTL__333e5c804978e56f (
	clk,
	compute_done,
	crossbar_id,
	crossbar_outport,
	ctrl_addr_inport,
	prologue_count_inport,
	reset,
	tile_id,
	recv_data__msg,
	recv_data__rdy,
	recv_data__val,
	recv_opt__msg,
	recv_opt__rdy,
	recv_opt__val,
	send_data__msg,
	send_data__rdy,
	send_data__val
);
	input wire [0:0] clk;
	input wire [0:0] compute_done;
	input wire [0:0] crossbar_id;
	input wire [47:0] crossbar_outport;
	input wire [2:0] ctrl_addr_inport;
	input wire [143:0] prologue_count_inport;
	input wire [0:0] reset;
	input wire [2:0] tile_id;
	input wire [279:0] recv_data__msg;
	output reg [7:0] recv_data__rdy;
	input wire [7:0] recv_data__val;
	input wire [137:0] recv_opt__msg;
	output reg [0:0] recv_opt__rdy;
	input wire [0:0] recv_opt__val;
	output reg [419:0] send_data__msg;
	input wire [11:0] send_data__rdy;
	output reg [11:0] send_data__val;
	localparam [3:0] __const__num_inports_at_update_signal = 4'd8;
	localparam [3:0] __const__num_outports_at_update_signal = 4'd12;
	localparam [5:0] __const__OPT_START = 6'd0;
	localparam [2:0] __const__ctrl_mem_size_at_update_prologue_counter = 3'd6;
	localparam [3:0] __const__num_inports_at_update_prologue_counter = 4'd8;
	localparam [2:0] __const__ctrl_mem_size_at_update_prologue_counter_next = 3'd6;
	localparam [3:0] __const__num_inports_at_update_prologue_counter_next = 4'd8;
	localparam [3:0] __const__num_outports_at_update_prologue_counter_next = 4'd12;
	localparam [3:0] __const__num_outports_at_update_prologue_allowing_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_prologue_or_valid_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_in_dir_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_rdy_vector = 4'd12;
	localparam [3:0] __const__outport_towards_local_base_id_at_update_rdy_vector = 4'd8;
	localparam [3:0] __const__num_outports_at_update_valid_vector = 4'd12;
	localparam [3:0] __const__num_inports_at_update_recv_required_vector = 4'd8;
	localparam [3:0] __const__num_outports_at_update_recv_required_vector = 4'd12;
	localparam [3:0] __const__num_outports_at_update_send_required_vector = 4'd12;
	reg [3:0] in_dir [0:11];
	reg [2:0] in_dir_local [0:11];
	reg [11:0] prologue_allowing_vector;
	wire [2:0] prologue_count_wire [0:5][0:7];
	reg [2:0] prologue_counter [0:5][0:7];
	reg [2:0] prologue_counter_next [0:5][0:7];
	wire [34:0] recv_data_msg [0:7];
	wire [0:0] recv_data_val [0:7];
	reg [7:0] recv_required_vector;
	reg [11:0] recv_valid_or_prologue_allowing_vector;
	reg [11:0] recv_valid_vector;
	reg [11:0] send_rdy_vector;
	reg [11:0] send_required_vector;
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	function automatic [2:0] sv2v_cast_3;
		input reg [2:0] inp;
		sv2v_cast_3 = inp;
	endfunction
	always @(*) begin : update_in_dir_vector
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_in_dir_vector; i = i + 1'd1)
				begin
					in_dir[sv2v_cast_4(i)] = 4'd0;
					in_dir_local[sv2v_cast_4(i)] = 3'd0;
				end
		end
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_in_dir_vector; i = i + 1'd1)
				begin
					in_dir[sv2v_cast_4(i)] = crossbar_outport[(11 - sv2v_cast_4(i)) * 4+:4];
					if (in_dir[sv2v_cast_4(i)] > 4'd0)
						in_dir_local[sv2v_cast_4(i)] = sv2v_cast_3(in_dir[sv2v_cast_4(i)] - 4'd1);
				end
		end
	end
	always @(*) begin : update_prologue_allowing_vector
		prologue_allowing_vector = 12'd0;
		begin : sv2v_autoblock_3
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_prologue_allowing_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 4'd0)
					prologue_allowing_vector[sv2v_cast_4(i)] = prologue_counter[ctrl_addr_inport][in_dir_local[sv2v_cast_4(i)]] < prologue_count_wire[ctrl_addr_inport][in_dir_local[sv2v_cast_4(i)]];
				else
					prologue_allowing_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(*) begin : update_prologue_counter_next
		begin : sv2v_autoblock_4
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_counter_next; addr = addr + 1'd1)
				begin : sv2v_autoblock_5
					reg [31:0] i;
					for (i = 1'd0; i < __const__num_inports_at_update_prologue_counter_next; i = i + 1'd1)
						begin
							prologue_counter_next[sv2v_cast_3(addr)][sv2v_cast_3(i)] = prologue_counter[sv2v_cast_3(addr)][sv2v_cast_3(i)];
							begin : sv2v_autoblock_6
								reg [31:0] j;
								for (j = 1'd0; j < __const__num_outports_at_update_prologue_counter_next; j = j + 1'd1)
									if ((((recv_opt__rdy & (in_dir[sv2v_cast_4(j)] > 4'd0)) & (in_dir_local[sv2v_cast_4(j)] == sv2v_cast_3(i))) & (sv2v_cast_3(addr) == ctrl_addr_inport)) & (prologue_counter[sv2v_cast_3(addr)][sv2v_cast_3(i)] < prologue_count_wire[sv2v_cast_3(addr)][sv2v_cast_3(i)]))
										prologue_counter_next[sv2v_cast_3(addr)][sv2v_cast_3(i)] = prologue_counter[sv2v_cast_3(addr)][sv2v_cast_3(i)] + 3'd1;
							end
						end
				end
		end
	end
	always @(*) begin : update_prologue_or_valid_vector
		recv_valid_or_prologue_allowing_vector = 12'd0;
		begin : sv2v_autoblock_7
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_prologue_or_valid_vector; i = i + 1'd1)
				recv_valid_or_prologue_allowing_vector[sv2v_cast_4(i)] = recv_valid_vector[sv2v_cast_4(i)] | prologue_allowing_vector[sv2v_cast_4(i)];
		end
	end
	always @(*) begin : update_rdy_vector
		send_rdy_vector = 12'd0;
		begin : sv2v_autoblock_8
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_rdy_vector; i = i + 1'd1)
				if ((in_dir[sv2v_cast_4(i)] > 4'd0) & (~compute_done | (sv2v_cast_4(i) < __const__outport_towards_local_base_id_at_update_rdy_vector)))
					send_rdy_vector[sv2v_cast_4(i)] = send_data__rdy[11 - sv2v_cast_4(i)+:1];
				else
					send_rdy_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(*) begin : update_recv_required_vector
		begin : sv2v_autoblock_9
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_update_recv_required_vector; i = i + 1'd1)
				recv_required_vector[sv2v_cast_3(i)] = 1'd0;
		end
		begin : sv2v_autoblock_10
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_recv_required_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 4'd0)
					recv_required_vector[in_dir_local[sv2v_cast_4(i)]] = 1'd1;
		end
	end
	always @(*) begin : update_send_required_vector
		begin : sv2v_autoblock_11
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_send_required_vector; i = i + 1'd1)
				send_required_vector[sv2v_cast_4(i)] = 1'd0;
		end
		begin : sv2v_autoblock_12
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_send_required_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 4'd0)
					send_required_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(*) begin : update_signal
		begin : sv2v_autoblock_13
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_inports_at_update_signal; i = i + 1'd1)
				recv_data__rdy[7 - sv2v_cast_3(i)+:1] = 1'd0;
		end
		begin : sv2v_autoblock_14
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_signal; i = i + 1'd1)
				begin
					send_data__val[11 - sv2v_cast_4(i)+:1] = 1'd0;
					send_data__msg[(11 - sv2v_cast_4(i)) * 35+:35] = 35'h000000000;
				end
		end
		recv_opt__rdy = 1'd0;
		if (recv_opt__val & (recv_opt__msg[137-:6] != __const__OPT_START)) begin
			begin : sv2v_autoblock_15
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_inports_at_update_signal; i = i + 1'd1)
					recv_data__rdy[7 - sv2v_cast_3(i)+:1] = (&recv_valid_vector & &send_rdy_vector) & recv_required_vector[sv2v_cast_3(i)];
			end
			begin : sv2v_autoblock_16
				reg [31:0] i;
				for (i = 1'd0; i < __const__num_outports_at_update_signal; i = i + 1'd1)
					begin
						send_data__val[11 - sv2v_cast_4(i)+:1] = &recv_valid_vector & send_required_vector[sv2v_cast_4(i)];
						if (&recv_valid_vector & send_required_vector[sv2v_cast_4(i)]) begin
							send_data__msg[((11 - sv2v_cast_4(i)) * 35) + 34-:32] = recv_data_msg[in_dir_local[sv2v_cast_4(i)]][34-:32];
							send_data__msg[((11 - sv2v_cast_4(i)) * 35) + 2] = recv_data_msg[in_dir_local[sv2v_cast_4(i)]][2];
						end
					end
			end
			recv_opt__rdy = &send_rdy_vector & &recv_valid_or_prologue_allowing_vector;
		end
	end
	always @(*) begin : update_valid_vector
		recv_valid_vector = 12'd0;
		begin : sv2v_autoblock_17
			reg [31:0] i;
			for (i = 1'd0; i < __const__num_outports_at_update_valid_vector; i = i + 1'd1)
				if (in_dir[sv2v_cast_4(i)] > 4'd0)
					recv_valid_vector[sv2v_cast_4(i)] = recv_data_val[in_dir_local[sv2v_cast_4(i)]];
				else
					recv_valid_vector[sv2v_cast_4(i)] = 1'd1;
		end
	end
	always @(posedge clk) begin : update_prologue_counter
		if (reset) begin : sv2v_autoblock_18
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_counter; addr = addr + 1'd1)
				begin : sv2v_autoblock_19
					reg [31:0] i;
					for (i = 1'd0; i < __const__num_inports_at_update_prologue_counter; i = i + 1'd1)
						prologue_counter[sv2v_cast_3(addr)][sv2v_cast_3(i)] <= 3'd0;
				end
		end
		else begin : sv2v_autoblock_20
			reg [31:0] addr;
			for (addr = 1'd0; addr < __const__ctrl_mem_size_at_update_prologue_counter; addr = addr + 1'd1)
				begin : sv2v_autoblock_21
					reg [31:0] i;
					for (i = 1'd0; i < __const__num_inports_at_update_prologue_counter; i = i + 1'd1)
						prologue_counter[sv2v_cast_3(addr)][sv2v_cast_3(i)] <= prologue_counter_next[sv2v_cast_3(addr)][sv2v_cast_3(i)];
				end
		end
	end
	assign recv_data_msg[0] = recv_data__msg[245+:35];
	assign recv_data_val[0] = recv_data__val[7+:1];
	assign recv_data_msg[1] = recv_data__msg[210+:35];
	assign recv_data_val[1] = recv_data__val[6+:1];
	assign recv_data_msg[2] = recv_data__msg[175+:35];
	assign recv_data_val[2] = recv_data__val[5+:1];
	assign recv_data_msg[3] = recv_data__msg[140+:35];
	assign recv_data_val[3] = recv_data__val[4+:1];
	assign recv_data_msg[4] = recv_data__msg[105+:35];
	assign recv_data_val[4] = recv_data__val[3+:1];
	assign recv_data_msg[5] = recv_data__msg[70+:35];
	assign recv_data_val[5] = recv_data__val[2+:1];
	assign recv_data_msg[6] = recv_data__msg[35+:35];
	assign recv_data_val[6] = recv_data__val[1+:1];
	assign recv_data_msg[7] = recv_data__msg[0+:35];
	assign recv_data_val[7] = recv_data__val[0+:1];
	assign prologue_count_wire[0][0] = prologue_count_inport[141+:3];
	assign prologue_count_wire[0][1] = prologue_count_inport[138+:3];
	assign prologue_count_wire[0][2] = prologue_count_inport[135+:3];
	assign prologue_count_wire[0][3] = prologue_count_inport[132+:3];
	assign prologue_count_wire[0][4] = prologue_count_inport[129+:3];
	assign prologue_count_wire[0][5] = prologue_count_inport[126+:3];
	assign prologue_count_wire[0][6] = prologue_count_inport[123+:3];
	assign prologue_count_wire[0][7] = prologue_count_inport[120+:3];
	assign prologue_count_wire[1][0] = prologue_count_inport[117+:3];
	assign prologue_count_wire[1][1] = prologue_count_inport[114+:3];
	assign prologue_count_wire[1][2] = prologue_count_inport[111+:3];
	assign prologue_count_wire[1][3] = prologue_count_inport[108+:3];
	assign prologue_count_wire[1][4] = prologue_count_inport[105+:3];
	assign prologue_count_wire[1][5] = prologue_count_inport[102+:3];
	assign prologue_count_wire[1][6] = prologue_count_inport[99+:3];
	assign prologue_count_wire[1][7] = prologue_count_inport[96+:3];
	assign prologue_count_wire[2][0] = prologue_count_inport[93+:3];
	assign prologue_count_wire[2][1] = prologue_count_inport[90+:3];
	assign prologue_count_wire[2][2] = prologue_count_inport[87+:3];
	assign prologue_count_wire[2][3] = prologue_count_inport[84+:3];
	assign prologue_count_wire[2][4] = prologue_count_inport[81+:3];
	assign prologue_count_wire[2][5] = prologue_count_inport[78+:3];
	assign prologue_count_wire[2][6] = prologue_count_inport[75+:3];
	assign prologue_count_wire[2][7] = prologue_count_inport[72+:3];
	assign prologue_count_wire[3][0] = prologue_count_inport[69+:3];
	assign prologue_count_wire[3][1] = prologue_count_inport[66+:3];
	assign prologue_count_wire[3][2] = prologue_count_inport[63+:3];
	assign prologue_count_wire[3][3] = prologue_count_inport[60+:3];
	assign prologue_count_wire[3][4] = prologue_count_inport[57+:3];
	assign prologue_count_wire[3][5] = prologue_count_inport[54+:3];
	assign prologue_count_wire[3][6] = prologue_count_inport[51+:3];
	assign prologue_count_wire[3][7] = prologue_count_inport[48+:3];
	assign prologue_count_wire[4][0] = prologue_count_inport[45+:3];
	assign prologue_count_wire[4][1] = prologue_count_inport[42+:3];
	assign prologue_count_wire[4][2] = prologue_count_inport[39+:3];
	assign prologue_count_wire[4][3] = prologue_count_inport[36+:3];
	assign prologue_count_wire[4][4] = prologue_count_inport[33+:3];
	assign prologue_count_wire[4][5] = prologue_count_inport[30+:3];
	assign prologue_count_wire[4][6] = prologue_count_inport[27+:3];
	assign prologue_count_wire[4][7] = prologue_count_inport[24+:3];
	assign prologue_count_wire[5][0] = prologue_count_inport[21+:3];
	assign prologue_count_wire[5][1] = prologue_count_inport[18+:3];
	assign prologue_count_wire[5][2] = prologue_count_inport[15+:3];
	assign prologue_count_wire[5][3] = prologue_count_inport[12+:3];
	assign prologue_count_wire[5][4] = prologue_count_inport[9+:3];
	assign prologue_count_wire[5][5] = prologue_count_inport[6+:3];
	assign prologue_count_wire[5][6] = prologue_count_inport[3+:3];
	assign prologue_count_wire[5][7] = prologue_count_inport[0+:3];
endmodule
module RegisterFile__da749a1852bb59a5 (
	clk,
	raddr,
	rdata,
	reset,
	waddr,
	wdata,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	output reg [34:0] rdata;
	input wire [0:0] reset;
	input wire [0:0] waddr;
	input wire [34:0] wdata;
	input wire [0:0] wen;
	localparam [0:0] __const__rd_ports_at_up_rf_read = 1'd1;
	localparam [0:0] __const__wr_ports_at_up_rf_write = 1'd1;
	reg [34:0] regs [0:1];
	function automatic [0:0] sv2v_cast_1;
		input reg [0:0] inp;
		sv2v_cast_1 = inp;
	endfunction
	always @(*) begin : up_rf_read
		begin : sv2v_autoblock_1
			reg [31:0] i;
			for (i = 1'd0; i < __const__rd_ports_at_up_rf_read; i = i + 1'd1)
				rdata[sv2v_cast_1(i) * 35+:35] = regs[raddr[sv2v_cast_1(i)+:1]];
		end
	end
	always @(posedge clk) begin : up_rf_write
		begin : sv2v_autoblock_2
			reg [31:0] i;
			for (i = 1'd0; i < __const__wr_ports_at_up_rf_write; i = i + 1'd1)
				if (wen[sv2v_cast_1(i)+:1])
					regs[waddr[sv2v_cast_1(i)+:1]] <= wdata[sv2v_cast_1(i) * 35+:35];
		end
	end
endmodule
module NormalQueueDpathRTL__e10c2d77bcb9538e (
	clk,
	raddr,
	recv_msg,
	reset,
	send_msg,
	waddr,
	wen
);
	input wire [0:0] clk;
	input wire [0:0] raddr;
	input wire [34:0] recv_msg;
	input wire [0:0] reset;
	output wire [34:0] send_msg;
	input wire [0:0] waddr;
	input wire [0:0] wen;
	wire [0:0] rf__clk;
	wire [0:0] rf__raddr;
	wire [34:0] rf__rdata;
	wire [0:0] rf__reset;
	wire [0:0] rf__waddr;
	wire [34:0] rf__wdata;
	wire [0:0] rf__wen;
	RegisterFile__da749a1852bb59a5 rf(
		.clk(rf__clk),
		.raddr(rf__raddr),
		.rdata(rf__rdata),
		.reset(rf__reset),
		.waddr(rf__waddr),
		.wdata(rf__wdata),
		.wen(rf__wen)
	);
	assign rf__clk = clk;
	assign rf__reset = reset;
	assign rf__raddr[0+:1] = raddr;
	assign send_msg = rf__rdata[0+:35];
	assign rf__wen[0+:1] = wen;
	assign rf__waddr[0+:1] = waddr;
	assign rf__wdata[0+:35] = recv_msg;
endmodule
module NormalQueueRTL__e10c2d77bcb9538e (
	clk,
	count,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	output wire [1:0] count;
	input wire [0:0] reset;
	input wire [34:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [34:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] ctrl__clk;
	wire [1:0] ctrl__count;
	wire [0:0] ctrl__raddr;
	wire [0:0] ctrl__recv_rdy;
	wire [0:0] ctrl__recv_val;
	wire [0:0] ctrl__reset;
	wire [0:0] ctrl__send_rdy;
	wire [0:0] ctrl__send_val;
	wire [0:0] ctrl__waddr;
	wire [0:0] ctrl__wen;
	NormalQueueCtrlRTL__num_entries_2 ctrl(
		.clk(ctrl__clk),
		.count(ctrl__count),
		.raddr(ctrl__raddr),
		.recv_rdy(ctrl__recv_rdy),
		.recv_val(ctrl__recv_val),
		.reset(ctrl__reset),
		.send_rdy(ctrl__send_rdy),
		.send_val(ctrl__send_val),
		.waddr(ctrl__waddr),
		.wen(ctrl__wen)
	);
	wire [0:0] dpath__clk;
	wire [0:0] dpath__raddr;
	wire [34:0] dpath__recv_msg;
	wire [0:0] dpath__reset;
	wire [34:0] dpath__send_msg;
	wire [0:0] dpath__waddr;
	wire [0:0] dpath__wen;
	NormalQueueDpathRTL__e10c2d77bcb9538e dpath(
		.clk(dpath__clk),
		.raddr(dpath__raddr),
		.recv_msg(dpath__recv_msg),
		.reset(dpath__reset),
		.send_msg(dpath__send_msg),
		.waddr(dpath__waddr),
		.wen(dpath__wen)
	);
	assign ctrl__clk = clk;
	assign ctrl__reset = reset;
	assign dpath__clk = clk;
	assign dpath__reset = reset;
	assign dpath__wen = ctrl__wen;
	assign dpath__waddr = ctrl__waddr;
	assign dpath__raddr = ctrl__raddr;
	assign ctrl__recv_val = recv__val;
	assign recv__rdy = ctrl__recv_rdy;
	assign dpath__recv_msg = recv__msg;
	assign send__val = ctrl__send_val;
	assign ctrl__send_rdy = send__rdy;
	assign send__msg = dpath__send_msg;
	assign count = ctrl__count;
endmodule
module ChannelRTL__d316842813c529a6 (
	clk,
	reset,
	recv__msg,
	recv__rdy,
	recv__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [34:0] recv__msg;
	output wire [0:0] recv__rdy;
	input wire [0:0] recv__val;
	output wire [34:0] send__msg;
	input wire [0:0] send__rdy;
	output wire [0:0] send__val;
	wire [0:0] queues__clk [0:0];
	wire [1:0] queues__count [0:0];
	wire [0:0] queues__reset [0:0];
	wire [34:0] queues__recv__msg [0:0];
	wire [0:0] queues__recv__rdy [0:0];
	wire [0:0] queues__recv__val [0:0];
	wire [34:0] queues__send__msg [0:0];
	wire [0:0] queues__send__rdy [0:0];
	wire [0:0] queues__send__val [0:0];
	NormalQueueRTL__e10c2d77bcb9538e queues__0(
		.clk(queues__clk[0]),
		.count(queues__count[0]),
		.reset(queues__reset[0]),
		.recv__msg(queues__recv__msg[0]),
		.recv__rdy(queues__recv__rdy[0]),
		.recv__val(queues__recv__val[0]),
		.send__msg(queues__send__msg[0]),
		.send__rdy(queues__send__rdy[0]),
		.send__val(queues__send__val[0])
	);
	assign queues__clk[0] = clk;
	assign queues__reset[0] = reset;
	assign queues__recv__msg[0] = recv__msg;
	assign recv__rdy = queues__recv__rdy[0];
	assign queues__recv__val[0] = recv__val;
	assign send__msg = queues__send__msg[0];
	assign queues__send__rdy[0] = send__rdy;
	assign send__val = queues__send__val[0];
endmodule
module LinkOrRTL__a54ca58e7852ace8 (
	clk,
	reset,
	recv_fu__msg,
	recv_fu__rdy,
	recv_fu__val,
	recv_xbar__msg,
	recv_xbar__rdy,
	recv_xbar__val,
	send__msg,
	send__rdy,
	send__val
);
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [34:0] recv_fu__msg;
	output reg [0:0] recv_fu__rdy;
	input wire [0:0] recv_fu__val;
	input wire [34:0] recv_xbar__msg;
	output reg [0:0] recv_xbar__rdy;
	input wire [0:0] recv_xbar__val;
	output reg [34:0] send__msg;
	input wire [0:0] send__rdy;
	output reg [0:0] send__val;
	always @(*) begin : process
		send__msg = 35'h000000000;
		send__msg[2] = recv_fu__msg[2] | recv_xbar__msg[2];
		send__msg[34-:32] = recv_xbar__msg[34-:32] | recv_fu__msg[34-:32];
		send__val = recv_fu__val | recv_xbar__val;
		recv_fu__rdy = send__rdy;
		recv_xbar__rdy = send__rdy;
	end
endmodule
module TileRTL__5c45db0fc5682835 (
	cgra_id,
	clk,
	reset,
	tile_id,
	from_mem_rdata__msg,
	from_mem_rdata__rdy,
	from_mem_rdata__val,
	recv_data__msg,
	recv_data__rdy,
	recv_data__val,
	recv_from_controller_pkt__msg,
	recv_from_controller_pkt__rdy,
	recv_from_controller_pkt__val,
	send_data__msg,
	send_data__rdy,
	send_data__val,
	send_to_controller_pkt__msg,
	send_to_controller_pkt__rdy,
	send_to_controller_pkt__val,
	to_mem_raddr__msg,
	to_mem_raddr__rdy,
	to_mem_raddr__val,
	to_mem_waddr__msg,
	to_mem_waddr__rdy,
	to_mem_waddr__val,
	to_mem_wdata__msg,
	to_mem_wdata__rdy,
	to_mem_wdata__val
);
	input wire [1:0] cgra_id;
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [2:0] tile_id;
	input wire [34:0] from_mem_rdata__msg;
	output wire [0:0] from_mem_rdata__rdy;
	input wire [0:0] from_mem_rdata__val;
	input wire [279:0] recv_data__msg;
	output wire [7:0] recv_data__rdy;
	input wire [7:0] recv_data__val;
	input wire [207:0] recv_from_controller_pkt__msg;
	output reg [0:0] recv_from_controller_pkt__rdy;
	input wire [0:0] recv_from_controller_pkt__val;
	output wire [279:0] send_data__msg;
	input wire [7:0] send_data__rdy;
	output wire [7:0] send_data__val;
	output reg [207:0] send_to_controller_pkt__msg;
	input wire [0:0] send_to_controller_pkt__rdy;
	output reg [0:0] send_to_controller_pkt__val;
	output wire [2:0] to_mem_raddr__msg;
	input wire [0:0] to_mem_raddr__rdy;
	output wire [0:0] to_mem_raddr__val;
	output wire [2:0] to_mem_waddr__msg;
	input wire [0:0] to_mem_waddr__rdy;
	output wire [0:0] to_mem_waddr__val;
	output wire [34:0] to_mem_wdata__msg;
	input wire [0:0] to_mem_wdata__rdy;
	output wire [0:0] to_mem_wdata__val;
	localparam [1:0] __const__CMD_CONFIG = 2'd3;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_FU = 3'd4;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR = 3'd5;
	localparam [2:0] __const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR = 3'd6;
	localparam [2:0] __const__CMD_CONFIG_TOTAL_CTRL_COUNT = 3'd7;
	localparam [3:0] __const__CMD_CONFIG_COUNT_PER_ITER = 4'd8;
	localparam [0:0] __const__CMD_LAUNCH = 1'd0;
	localparam [3:0] __const__CMD_CONST = 4'd13;
	reg [0:0] element_done;
	reg [0:0] fu_crossbar_done;
	reg [0:0] routing_crossbar_done;
	wire [0:0] const_mem__clk;
	reg [0:0] const_mem__ctrl_proceed;
	wire [0:0] const_mem__reset;
	reg [34:0] const_mem__recv_const__msg;
	wire [0:0] const_mem__recv_const__rdy;
	reg [0:0] const_mem__recv_const__val;
	wire [34:0] const_mem__send_const__msg;
	wire [0:0] const_mem__send_const__rdy;
	wire [0:0] const_mem__send_const__val;
	ConstQueueDynamicRTL__8f4d11f2dd80f063 const_mem(
		.clk(const_mem__clk),
		.ctrl_proceed(const_mem__ctrl_proceed),
		.reset(const_mem__reset),
		.recv_const__msg(const_mem__recv_const__msg),
		.recv_const__rdy(const_mem__recv_const__rdy),
		.recv_const__val(const_mem__recv_const__val),
		.send_const__msg(const_mem__send_const__msg),
		.send_const__rdy(const_mem__send_const__rdy),
		.send_const__val(const_mem__send_const__val)
	);
	wire [1:0] ctrl_mem__cgra_id;
	wire [0:0] ctrl_mem__clk;
	wire [2:0] ctrl_mem__ctrl_addr_outport;
	wire [2:0] ctrl_mem__prologue_count_outport_fu;
	wire [35:0] ctrl_mem__prologue_count_outport_fu_crossbar;
	wire [143:0] ctrl_mem__prologue_count_outport_routing_crossbar;
	wire [0:0] ctrl_mem__reset;
	wire [2:0] ctrl_mem__tile_id;
	reg [207:0] ctrl_mem__recv_pkt_from_controller__msg;
	wire [0:0] ctrl_mem__recv_pkt_from_controller__rdy;
	reg [0:0] ctrl_mem__recv_pkt_from_controller__val;
	wire [137:0] ctrl_mem__send_ctrl__msg;
	reg [0:0] ctrl_mem__send_ctrl__rdy;
	wire [0:0] ctrl_mem__send_ctrl__val;
	wire [207:0] ctrl_mem__send_pkt_to_controller__msg;
	reg [0:0] ctrl_mem__send_pkt_to_controller__rdy;
	wire [0:0] ctrl_mem__send_pkt_to_controller__val;
	CtrlMemDynamicRTL__3bcda19edfae4ca2 ctrl_mem(
		.cgra_id(ctrl_mem__cgra_id),
		.clk(ctrl_mem__clk),
		.ctrl_addr_outport(ctrl_mem__ctrl_addr_outport),
		.prologue_count_outport_fu(ctrl_mem__prologue_count_outport_fu),
		.prologue_count_outport_fu_crossbar(ctrl_mem__prologue_count_outport_fu_crossbar),
		.prologue_count_outport_routing_crossbar(ctrl_mem__prologue_count_outport_routing_crossbar),
		.reset(ctrl_mem__reset),
		.tile_id(ctrl_mem__tile_id),
		.recv_pkt_from_controller__msg(ctrl_mem__recv_pkt_from_controller__msg),
		.recv_pkt_from_controller__rdy(ctrl_mem__recv_pkt_from_controller__rdy),
		.recv_pkt_from_controller__val(ctrl_mem__recv_pkt_from_controller__val),
		.send_ctrl__msg(ctrl_mem__send_ctrl__msg),
		.send_ctrl__rdy(ctrl_mem__send_ctrl__rdy),
		.send_ctrl__val(ctrl_mem__send_ctrl__val),
		.send_pkt_to_controller__msg(ctrl_mem__send_pkt_to_controller__msg),
		.send_pkt_to_controller__rdy(ctrl_mem__send_pkt_to_controller__rdy),
		.send_pkt_to_controller__val(ctrl_mem__send_pkt_to_controller__val)
	);
	wire [0:0] element__clk;
	wire [2:0] element__prologue_count_inport;
	wire [0:0] element__reset;
	wire [2:0] element__tile_id;
	wire [104:0] element__from_mem_rdata__msg;
	wire [2:0] element__from_mem_rdata__rdy;
	wire [2:0] element__from_mem_rdata__val;
	wire [34:0] element__recv_const__msg;
	wire [0:0] element__recv_const__rdy;
	wire [0:0] element__recv_const__val;
	wire [139:0] element__recv_in__msg;
	wire [3:0] element__recv_in__rdy;
	wire [3:0] element__recv_in__val;
	reg [137:0] element__recv_opt__msg;
	wire [0:0] element__recv_opt__rdy;
	reg [0:0] element__recv_opt__val;
	wire [69:0] element__send_out__msg;
	wire [1:0] element__send_out__rdy;
	wire [1:0] element__send_out__val;
	wire [8:0] element__to_mem_raddr__msg;
	wire [2:0] element__to_mem_raddr__rdy;
	wire [2:0] element__to_mem_raddr__val;
	wire [8:0] element__to_mem_waddr__msg;
	wire [2:0] element__to_mem_waddr__rdy;
	wire [2:0] element__to_mem_waddr__val;
	wire [104:0] element__to_mem_wdata__msg;
	wire [2:0] element__to_mem_wdata__rdy;
	wire [2:0] element__to_mem_wdata__val;
	FlexibleFuRTL__91ead62b2a3425ea element(
		.clk(element__clk),
		.prologue_count_inport(element__prologue_count_inport),
		.reset(element__reset),
		.tile_id(element__tile_id),
		.from_mem_rdata__msg(element__from_mem_rdata__msg),
		.from_mem_rdata__rdy(element__from_mem_rdata__rdy),
		.from_mem_rdata__val(element__from_mem_rdata__val),
		.recv_const__msg(element__recv_const__msg),
		.recv_const__rdy(element__recv_const__rdy),
		.recv_const__val(element__recv_const__val),
		.recv_in__msg(element__recv_in__msg),
		.recv_in__rdy(element__recv_in__rdy),
		.recv_in__val(element__recv_in__val),
		.recv_opt__msg(element__recv_opt__msg),
		.recv_opt__rdy(element__recv_opt__rdy),
		.recv_opt__val(element__recv_opt__val),
		.send_out__msg(element__send_out__msg),
		.send_out__rdy(element__send_out__rdy),
		.send_out__val(element__send_out__val),
		.to_mem_raddr__msg(element__to_mem_raddr__msg),
		.to_mem_raddr__rdy(element__to_mem_raddr__rdy),
		.to_mem_raddr__val(element__to_mem_raddr__val),
		.to_mem_waddr__msg(element__to_mem_waddr__msg),
		.to_mem_waddr__rdy(element__to_mem_waddr__rdy),
		.to_mem_waddr__val(element__to_mem_waddr__val),
		.to_mem_wdata__msg(element__to_mem_wdata__msg),
		.to_mem_wdata__rdy(element__to_mem_wdata__rdy),
		.to_mem_wdata__val(element__to_mem_wdata__val)
	);
	wire [0:0] fu_crossbar__clk;
	reg [0:0] fu_crossbar__compute_done;
	wire [0:0] fu_crossbar__crossbar_id;
	wire [23:0] fu_crossbar__crossbar_outport;
	wire [2:0] fu_crossbar__ctrl_addr_inport;
	wire [35:0] fu_crossbar__prologue_count_inport;
	wire [0:0] fu_crossbar__reset;
	wire [2:0] fu_crossbar__tile_id;
	wire [69:0] fu_crossbar__recv_data__msg;
	wire [1:0] fu_crossbar__recv_data__rdy;
	wire [1:0] fu_crossbar__recv_data__val;
	reg [137:0] fu_crossbar__recv_opt__msg;
	wire [0:0] fu_crossbar__recv_opt__rdy;
	reg [0:0] fu_crossbar__recv_opt__val;
	wire [419:0] fu_crossbar__send_data__msg;
	wire [11:0] fu_crossbar__send_data__rdy;
	wire [11:0] fu_crossbar__send_data__val;
	CrossbarRTL__542f2f2c623caccb fu_crossbar(
		.clk(fu_crossbar__clk),
		.compute_done(fu_crossbar__compute_done),
		.crossbar_id(fu_crossbar__crossbar_id),
		.crossbar_outport(fu_crossbar__crossbar_outport),
		.ctrl_addr_inport(fu_crossbar__ctrl_addr_inport),
		.prologue_count_inport(fu_crossbar__prologue_count_inport),
		.reset(fu_crossbar__reset),
		.tile_id(fu_crossbar__tile_id),
		.recv_data__msg(fu_crossbar__recv_data__msg),
		.recv_data__rdy(fu_crossbar__recv_data__rdy),
		.recv_data__val(fu_crossbar__recv_data__val),
		.recv_opt__msg(fu_crossbar__recv_opt__msg),
		.recv_opt__rdy(fu_crossbar__recv_opt__rdy),
		.recv_opt__val(fu_crossbar__recv_opt__val),
		.send_data__msg(fu_crossbar__send_data__msg),
		.send_data__rdy(fu_crossbar__send_data__rdy),
		.send_data__val(fu_crossbar__send_data__val)
	);
	wire [0:0] register_cluster__clk;
	wire [137:0] register_cluster__inport_opt;
	wire [0:0] register_cluster__reset;
	wire [139:0] register_cluster__recv_data_from_const__msg;
	wire [3:0] register_cluster__recv_data_from_const__rdy;
	wire [3:0] register_cluster__recv_data_from_const__val;
	wire [139:0] register_cluster__recv_data_from_fu_crossbar__msg;
	wire [3:0] register_cluster__recv_data_from_fu_crossbar__rdy;
	wire [3:0] register_cluster__recv_data_from_fu_crossbar__val;
	wire [139:0] register_cluster__recv_data_from_routing_crossbar__msg;
	wire [3:0] register_cluster__recv_data_from_routing_crossbar__rdy;
	wire [3:0] register_cluster__recv_data_from_routing_crossbar__val;
	wire [139:0] register_cluster__send_data_to_fu__msg;
	wire [3:0] register_cluster__send_data_to_fu__rdy;
	wire [3:0] register_cluster__send_data_to_fu__val;
	RegisterClusterRTL__a8b6c64c450b5f1b register_cluster(
		.clk(register_cluster__clk),
		.inport_opt(register_cluster__inport_opt),
		.reset(register_cluster__reset),
		.recv_data_from_const__msg(register_cluster__recv_data_from_const__msg),
		.recv_data_from_const__rdy(register_cluster__recv_data_from_const__rdy),
		.recv_data_from_const__val(register_cluster__recv_data_from_const__val),
		.recv_data_from_fu_crossbar__msg(register_cluster__recv_data_from_fu_crossbar__msg),
		.recv_data_from_fu_crossbar__rdy(register_cluster__recv_data_from_fu_crossbar__rdy),
		.recv_data_from_fu_crossbar__val(register_cluster__recv_data_from_fu_crossbar__val),
		.recv_data_from_routing_crossbar__msg(register_cluster__recv_data_from_routing_crossbar__msg),
		.recv_data_from_routing_crossbar__rdy(register_cluster__recv_data_from_routing_crossbar__rdy),
		.recv_data_from_routing_crossbar__val(register_cluster__recv_data_from_routing_crossbar__val),
		.send_data_to_fu__msg(register_cluster__send_data_to_fu__msg),
		.send_data_to_fu__rdy(register_cluster__send_data_to_fu__rdy),
		.send_data_to_fu__val(register_cluster__send_data_to_fu__val)
	);
	wire [0:0] routing_crossbar__clk;
	reg [0:0] routing_crossbar__compute_done;
	wire [0:0] routing_crossbar__crossbar_id;
	wire [47:0] routing_crossbar__crossbar_outport;
	wire [2:0] routing_crossbar__ctrl_addr_inport;
	wire [143:0] routing_crossbar__prologue_count_inport;
	wire [0:0] routing_crossbar__reset;
	wire [2:0] routing_crossbar__tile_id;
	wire [279:0] routing_crossbar__recv_data__msg;
	wire [7:0] routing_crossbar__recv_data__rdy;
	wire [7:0] routing_crossbar__recv_data__val;
	reg [137:0] routing_crossbar__recv_opt__msg;
	wire [0:0] routing_crossbar__recv_opt__rdy;
	reg [0:0] routing_crossbar__recv_opt__val;
	wire [419:0] routing_crossbar__send_data__msg;
	wire [11:0] routing_crossbar__send_data__rdy;
	wire [11:0] routing_crossbar__send_data__val;
	CrossbarRTL__333e5c804978e56f routing_crossbar(
		.clk(routing_crossbar__clk),
		.compute_done(routing_crossbar__compute_done),
		.crossbar_id(routing_crossbar__crossbar_id),
		.crossbar_outport(routing_crossbar__crossbar_outport),
		.ctrl_addr_inport(routing_crossbar__ctrl_addr_inport),
		.prologue_count_inport(routing_crossbar__prologue_count_inport),
		.reset(routing_crossbar__reset),
		.tile_id(routing_crossbar__tile_id),
		.recv_data__msg(routing_crossbar__recv_data__msg),
		.recv_data__rdy(routing_crossbar__recv_data__rdy),
		.recv_data__val(routing_crossbar__recv_data__val),
		.recv_opt__msg(routing_crossbar__recv_opt__msg),
		.recv_opt__rdy(routing_crossbar__recv_opt__rdy),
		.recv_opt__val(routing_crossbar__recv_opt__val),
		.send_data__msg(routing_crossbar__send_data__msg),
		.send_data__rdy(routing_crossbar__send_data__rdy),
		.send_data__val(routing_crossbar__send_data__val)
	);
	wire [0:0] tile_in_channel__clk [0:7];
	wire [0:0] tile_in_channel__reset [0:7];
	wire [34:0] tile_in_channel__recv__msg [0:7];
	wire [0:0] tile_in_channel__recv__rdy [0:7];
	wire [0:0] tile_in_channel__recv__val [0:7];
	wire [34:0] tile_in_channel__send__msg [0:7];
	wire [0:0] tile_in_channel__send__rdy [0:7];
	wire [0:0] tile_in_channel__send__val [0:7];
	ChannelRTL__d316842813c529a6 tile_in_channel__0(
		.clk(tile_in_channel__clk[0]),
		.reset(tile_in_channel__reset[0]),
		.recv__msg(tile_in_channel__recv__msg[0]),
		.recv__rdy(tile_in_channel__recv__rdy[0]),
		.recv__val(tile_in_channel__recv__val[0]),
		.send__msg(tile_in_channel__send__msg[0]),
		.send__rdy(tile_in_channel__send__rdy[0]),
		.send__val(tile_in_channel__send__val[0])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__1(
		.clk(tile_in_channel__clk[1]),
		.reset(tile_in_channel__reset[1]),
		.recv__msg(tile_in_channel__recv__msg[1]),
		.recv__rdy(tile_in_channel__recv__rdy[1]),
		.recv__val(tile_in_channel__recv__val[1]),
		.send__msg(tile_in_channel__send__msg[1]),
		.send__rdy(tile_in_channel__send__rdy[1]),
		.send__val(tile_in_channel__send__val[1])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__2(
		.clk(tile_in_channel__clk[2]),
		.reset(tile_in_channel__reset[2]),
		.recv__msg(tile_in_channel__recv__msg[2]),
		.recv__rdy(tile_in_channel__recv__rdy[2]),
		.recv__val(tile_in_channel__recv__val[2]),
		.send__msg(tile_in_channel__send__msg[2]),
		.send__rdy(tile_in_channel__send__rdy[2]),
		.send__val(tile_in_channel__send__val[2])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__3(
		.clk(tile_in_channel__clk[3]),
		.reset(tile_in_channel__reset[3]),
		.recv__msg(tile_in_channel__recv__msg[3]),
		.recv__rdy(tile_in_channel__recv__rdy[3]),
		.recv__val(tile_in_channel__recv__val[3]),
		.send__msg(tile_in_channel__send__msg[3]),
		.send__rdy(tile_in_channel__send__rdy[3]),
		.send__val(tile_in_channel__send__val[3])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__4(
		.clk(tile_in_channel__clk[4]),
		.reset(tile_in_channel__reset[4]),
		.recv__msg(tile_in_channel__recv__msg[4]),
		.recv__rdy(tile_in_channel__recv__rdy[4]),
		.recv__val(tile_in_channel__recv__val[4]),
		.send__msg(tile_in_channel__send__msg[4]),
		.send__rdy(tile_in_channel__send__rdy[4]),
		.send__val(tile_in_channel__send__val[4])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__5(
		.clk(tile_in_channel__clk[5]),
		.reset(tile_in_channel__reset[5]),
		.recv__msg(tile_in_channel__recv__msg[5]),
		.recv__rdy(tile_in_channel__recv__rdy[5]),
		.recv__val(tile_in_channel__recv__val[5]),
		.send__msg(tile_in_channel__send__msg[5]),
		.send__rdy(tile_in_channel__send__rdy[5]),
		.send__val(tile_in_channel__send__val[5])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__6(
		.clk(tile_in_channel__clk[6]),
		.reset(tile_in_channel__reset[6]),
		.recv__msg(tile_in_channel__recv__msg[6]),
		.recv__rdy(tile_in_channel__recv__rdy[6]),
		.recv__val(tile_in_channel__recv__val[6]),
		.send__msg(tile_in_channel__send__msg[6]),
		.send__rdy(tile_in_channel__send__rdy[6]),
		.send__val(tile_in_channel__send__val[6])
	);
	ChannelRTL__d316842813c529a6 tile_in_channel__7(
		.clk(tile_in_channel__clk[7]),
		.reset(tile_in_channel__reset[7]),
		.recv__msg(tile_in_channel__recv__msg[7]),
		.recv__rdy(tile_in_channel__recv__rdy[7]),
		.recv__val(tile_in_channel__recv__val[7]),
		.send__msg(tile_in_channel__send__msg[7]),
		.send__rdy(tile_in_channel__send__rdy[7]),
		.send__val(tile_in_channel__send__val[7])
	);
	wire [0:0] tile_out_or_link__clk [0:7];
	wire [0:0] tile_out_or_link__reset [0:7];
	wire [34:0] tile_out_or_link__recv_fu__msg [0:7];
	wire [0:0] tile_out_or_link__recv_fu__rdy [0:7];
	wire [0:0] tile_out_or_link__recv_fu__val [0:7];
	wire [34:0] tile_out_or_link__recv_xbar__msg [0:7];
	wire [0:0] tile_out_or_link__recv_xbar__rdy [0:7];
	wire [0:0] tile_out_or_link__recv_xbar__val [0:7];
	wire [34:0] tile_out_or_link__send__msg [0:7];
	wire [0:0] tile_out_or_link__send__rdy [0:7];
	wire [0:0] tile_out_or_link__send__val [0:7];
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__0(
		.clk(tile_out_or_link__clk[0]),
		.reset(tile_out_or_link__reset[0]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[0]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[0]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[0]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[0]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[0]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[0]),
		.send__msg(tile_out_or_link__send__msg[0]),
		.send__rdy(tile_out_or_link__send__rdy[0]),
		.send__val(tile_out_or_link__send__val[0])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__1(
		.clk(tile_out_or_link__clk[1]),
		.reset(tile_out_or_link__reset[1]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[1]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[1]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[1]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[1]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[1]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[1]),
		.send__msg(tile_out_or_link__send__msg[1]),
		.send__rdy(tile_out_or_link__send__rdy[1]),
		.send__val(tile_out_or_link__send__val[1])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__2(
		.clk(tile_out_or_link__clk[2]),
		.reset(tile_out_or_link__reset[2]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[2]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[2]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[2]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[2]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[2]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[2]),
		.send__msg(tile_out_or_link__send__msg[2]),
		.send__rdy(tile_out_or_link__send__rdy[2]),
		.send__val(tile_out_or_link__send__val[2])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__3(
		.clk(tile_out_or_link__clk[3]),
		.reset(tile_out_or_link__reset[3]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[3]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[3]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[3]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[3]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[3]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[3]),
		.send__msg(tile_out_or_link__send__msg[3]),
		.send__rdy(tile_out_or_link__send__rdy[3]),
		.send__val(tile_out_or_link__send__val[3])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__4(
		.clk(tile_out_or_link__clk[4]),
		.reset(tile_out_or_link__reset[4]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[4]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[4]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[4]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[4]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[4]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[4]),
		.send__msg(tile_out_or_link__send__msg[4]),
		.send__rdy(tile_out_or_link__send__rdy[4]),
		.send__val(tile_out_or_link__send__val[4])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__5(
		.clk(tile_out_or_link__clk[5]),
		.reset(tile_out_or_link__reset[5]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[5]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[5]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[5]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[5]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[5]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[5]),
		.send__msg(tile_out_or_link__send__msg[5]),
		.send__rdy(tile_out_or_link__send__rdy[5]),
		.send__val(tile_out_or_link__send__val[5])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__6(
		.clk(tile_out_or_link__clk[6]),
		.reset(tile_out_or_link__reset[6]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[6]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[6]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[6]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[6]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[6]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[6]),
		.send__msg(tile_out_or_link__send__msg[6]),
		.send__rdy(tile_out_or_link__send__rdy[6]),
		.send__val(tile_out_or_link__send__val[6])
	);
	LinkOrRTL__a54ca58e7852ace8 tile_out_or_link__7(
		.clk(tile_out_or_link__clk[7]),
		.reset(tile_out_or_link__reset[7]),
		.recv_fu__msg(tile_out_or_link__recv_fu__msg[7]),
		.recv_fu__rdy(tile_out_or_link__recv_fu__rdy[7]),
		.recv_fu__val(tile_out_or_link__recv_fu__val[7]),
		.recv_xbar__msg(tile_out_or_link__recv_xbar__msg[7]),
		.recv_xbar__rdy(tile_out_or_link__recv_xbar__rdy[7]),
		.recv_xbar__val(tile_out_or_link__recv_xbar__val[7]),
		.send__msg(tile_out_or_link__send__msg[7]),
		.send__rdy(tile_out_or_link__send__rdy[7]),
		.send__val(tile_out_or_link__send__val[7])
	);
	function automatic [3:0] sv2v_cast_4;
		input reg [3:0] inp;
		sv2v_cast_4 = inp;
	endfunction
	always @(*) begin : feed_pkt
		ctrl_mem__recv_pkt_from_controller__msg = 208'h0000000000000000000000000000000000000000000000000000;
		const_mem__recv_const__msg = 35'h000000000;
		ctrl_mem__recv_pkt_from_controller__val = 1'd0;
		const_mem__recv_const__val = 1'd0;
		recv_from_controller_pkt__rdy = 1'd0;
		if (recv_from_controller_pkt__val & (((((((recv_from_controller_pkt__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG)) | (recv_from_controller_pkt__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU))) | (recv_from_controller_pkt__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_FU_CROSSBAR))) | (recv_from_controller_pkt__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR))) | (recv_from_controller_pkt__msg[182-:4] == sv2v_cast_4(__const__CMD_CONFIG_TOTAL_CTRL_COUNT))) | (recv_from_controller_pkt__msg[182-:4] == __const__CMD_CONFIG_COUNT_PER_ITER)) | (recv_from_controller_pkt__msg[182-:4] == sv2v_cast_4(__const__CMD_LAUNCH)))) begin
			ctrl_mem__recv_pkt_from_controller__val = 1'd1;
			ctrl_mem__recv_pkt_from_controller__msg = recv_from_controller_pkt__msg;
			recv_from_controller_pkt__rdy = ctrl_mem__recv_pkt_from_controller__rdy;
		end
		else if (recv_from_controller_pkt__val & (recv_from_controller_pkt__msg[182-:4] == __const__CMD_CONST)) begin
			const_mem__recv_const__val = 1'd1;
			const_mem__recv_const__msg = recv_from_controller_pkt__msg[178-:35];
			recv_from_controller_pkt__rdy = const_mem__recv_const__rdy;
		end
	end
	always @(*) begin : notify_const_mem
		const_mem__ctrl_proceed = ctrl_mem__send_ctrl__rdy & ctrl_mem__send_ctrl__val;
	end
	always @(*) begin : notify_crossbars_compute_status
		routing_crossbar__compute_done = element_done;
		fu_crossbar__compute_done = element_done;
	end
	always @(*) begin : update_opt
		element__recv_opt__msg = ctrl_mem__send_ctrl__msg;
		routing_crossbar__recv_opt__msg = ctrl_mem__send_ctrl__msg;
		fu_crossbar__recv_opt__msg = ctrl_mem__send_ctrl__msg;
		element__recv_opt__val = ctrl_mem__send_ctrl__val & ~element_done;
		routing_crossbar__recv_opt__val = ctrl_mem__send_ctrl__val & ~routing_crossbar_done;
		fu_crossbar__recv_opt__val = ctrl_mem__send_ctrl__val & ~fu_crossbar_done;
		ctrl_mem__send_ctrl__rdy = ((element__recv_opt__rdy | element_done) & (routing_crossbar__recv_opt__rdy | routing_crossbar_done)) & (fu_crossbar__recv_opt__rdy | fu_crossbar_done);
	end
	always @(*) begin : update_send_out_signal
		send_to_controller_pkt__val = 1'd0;
		send_to_controller_pkt__msg = 208'h0000000000000000000000000000000000000000000000000000;
		if (ctrl_mem__send_pkt_to_controller__val) begin
			send_to_controller_pkt__val = 1'd1;
			send_to_controller_pkt__msg = ctrl_mem__send_pkt_to_controller__msg;
		end
		ctrl_mem__send_pkt_to_controller__rdy = send_to_controller_pkt__rdy;
	end
	always @(posedge clk) begin : already_done
		if (reset | ctrl_mem__send_ctrl__rdy) begin
			element_done <= 1'd0;
			fu_crossbar_done <= 1'd0;
			routing_crossbar_done <= 1'd0;
		end
		else begin
			if (element__recv_opt__rdy)
				element_done <= 1'd1;
			if (fu_crossbar__recv_opt__rdy)
				fu_crossbar_done <= 1'd1;
			if (routing_crossbar__recv_opt__rdy)
				routing_crossbar_done <= 1'd1;
		end
	end
	assign element__clk = clk;
	assign element__reset = reset;
	assign const_mem__clk = clk;
	assign const_mem__reset = reset;
	assign routing_crossbar__clk = clk;
	assign routing_crossbar__reset = reset;
	assign fu_crossbar__clk = clk;
	assign fu_crossbar__reset = reset;
	assign register_cluster__clk = clk;
	assign register_cluster__reset = reset;
	assign ctrl_mem__clk = clk;
	assign ctrl_mem__reset = reset;
	assign tile_in_channel__clk[0] = clk;
	assign tile_in_channel__reset[0] = reset;
	assign tile_in_channel__clk[1] = clk;
	assign tile_in_channel__reset[1] = reset;
	assign tile_in_channel__clk[2] = clk;
	assign tile_in_channel__reset[2] = reset;
	assign tile_in_channel__clk[3] = clk;
	assign tile_in_channel__reset[3] = reset;
	assign tile_in_channel__clk[4] = clk;
	assign tile_in_channel__reset[4] = reset;
	assign tile_in_channel__clk[5] = clk;
	assign tile_in_channel__reset[5] = reset;
	assign tile_in_channel__clk[6] = clk;
	assign tile_in_channel__reset[6] = reset;
	assign tile_in_channel__clk[7] = clk;
	assign tile_in_channel__reset[7] = reset;
	assign tile_out_or_link__clk[0] = clk;
	assign tile_out_or_link__reset[0] = reset;
	assign tile_out_or_link__clk[1] = clk;
	assign tile_out_or_link__reset[1] = reset;
	assign tile_out_or_link__clk[2] = clk;
	assign tile_out_or_link__reset[2] = reset;
	assign tile_out_or_link__clk[3] = clk;
	assign tile_out_or_link__reset[3] = reset;
	assign tile_out_or_link__clk[4] = clk;
	assign tile_out_or_link__reset[4] = reset;
	assign tile_out_or_link__clk[5] = clk;
	assign tile_out_or_link__reset[5] = reset;
	assign tile_out_or_link__clk[6] = clk;
	assign tile_out_or_link__reset[6] = reset;
	assign tile_out_or_link__clk[7] = clk;
	assign tile_out_or_link__reset[7] = reset;
	assign element__tile_id = tile_id;
	assign ctrl_mem__cgra_id = cgra_id;
	assign ctrl_mem__tile_id = tile_id;
	assign fu_crossbar__tile_id = tile_id;
	assign routing_crossbar__tile_id = tile_id;
	assign routing_crossbar__crossbar_id = 1'd0;
	assign fu_crossbar__crossbar_id = 1'd1;
	assign element__recv_const__msg = const_mem__send_const__msg;
	assign const_mem__send_const__rdy = element__recv_const__rdy;
	assign element__recv_const__val = const_mem__send_const__val;
	assign routing_crossbar__ctrl_addr_inport = ctrl_mem__ctrl_addr_outport;
	assign fu_crossbar__ctrl_addr_inport = ctrl_mem__ctrl_addr_outport;
	assign element__prologue_count_inport = ctrl_mem__prologue_count_outport_fu;
	assign routing_crossbar__prologue_count_inport[141+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[141+:3];
	assign routing_crossbar__prologue_count_inport[138+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[138+:3];
	assign routing_crossbar__prologue_count_inport[135+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[135+:3];
	assign routing_crossbar__prologue_count_inport[132+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[132+:3];
	assign routing_crossbar__prologue_count_inport[129+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[129+:3];
	assign routing_crossbar__prologue_count_inport[126+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[126+:3];
	assign routing_crossbar__prologue_count_inport[123+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[123+:3];
	assign routing_crossbar__prologue_count_inport[120+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[120+:3];
	assign fu_crossbar__prologue_count_inport[33+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[33+:3];
	assign fu_crossbar__prologue_count_inport[30+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[30+:3];
	assign routing_crossbar__prologue_count_inport[117+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[117+:3];
	assign routing_crossbar__prologue_count_inport[114+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[114+:3];
	assign routing_crossbar__prologue_count_inport[111+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[111+:3];
	assign routing_crossbar__prologue_count_inport[108+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[108+:3];
	assign routing_crossbar__prologue_count_inport[105+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[105+:3];
	assign routing_crossbar__prologue_count_inport[102+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[102+:3];
	assign routing_crossbar__prologue_count_inport[99+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[99+:3];
	assign routing_crossbar__prologue_count_inport[96+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[96+:3];
	assign fu_crossbar__prologue_count_inport[27+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[27+:3];
	assign fu_crossbar__prologue_count_inport[24+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[24+:3];
	assign routing_crossbar__prologue_count_inport[93+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[93+:3];
	assign routing_crossbar__prologue_count_inport[90+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[90+:3];
	assign routing_crossbar__prologue_count_inport[87+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[87+:3];
	assign routing_crossbar__prologue_count_inport[84+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[84+:3];
	assign routing_crossbar__prologue_count_inport[81+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[81+:3];
	assign routing_crossbar__prologue_count_inport[78+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[78+:3];
	assign routing_crossbar__prologue_count_inport[75+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[75+:3];
	assign routing_crossbar__prologue_count_inport[72+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[72+:3];
	assign fu_crossbar__prologue_count_inport[21+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[21+:3];
	assign fu_crossbar__prologue_count_inport[18+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[18+:3];
	assign routing_crossbar__prologue_count_inport[69+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[69+:3];
	assign routing_crossbar__prologue_count_inport[66+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[66+:3];
	assign routing_crossbar__prologue_count_inport[63+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[63+:3];
	assign routing_crossbar__prologue_count_inport[60+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[60+:3];
	assign routing_crossbar__prologue_count_inport[57+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[57+:3];
	assign routing_crossbar__prologue_count_inport[54+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[54+:3];
	assign routing_crossbar__prologue_count_inport[51+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[51+:3];
	assign routing_crossbar__prologue_count_inport[48+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[48+:3];
	assign fu_crossbar__prologue_count_inport[15+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[15+:3];
	assign fu_crossbar__prologue_count_inport[12+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[12+:3];
	assign routing_crossbar__prologue_count_inport[45+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[45+:3];
	assign routing_crossbar__prologue_count_inport[42+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[42+:3];
	assign routing_crossbar__prologue_count_inport[39+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[39+:3];
	assign routing_crossbar__prologue_count_inport[36+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[36+:3];
	assign routing_crossbar__prologue_count_inport[33+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[33+:3];
	assign routing_crossbar__prologue_count_inport[30+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[30+:3];
	assign routing_crossbar__prologue_count_inport[27+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[27+:3];
	assign routing_crossbar__prologue_count_inport[24+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[24+:3];
	assign fu_crossbar__prologue_count_inport[9+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[9+:3];
	assign fu_crossbar__prologue_count_inport[6+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[6+:3];
	assign routing_crossbar__prologue_count_inport[21+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[21+:3];
	assign routing_crossbar__prologue_count_inport[18+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[18+:3];
	assign routing_crossbar__prologue_count_inport[15+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[15+:3];
	assign routing_crossbar__prologue_count_inport[12+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[12+:3];
	assign routing_crossbar__prologue_count_inport[9+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[9+:3];
	assign routing_crossbar__prologue_count_inport[6+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[6+:3];
	assign routing_crossbar__prologue_count_inport[3+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[3+:3];
	assign routing_crossbar__prologue_count_inport[0+:3] = ctrl_mem__prologue_count_outport_routing_crossbar[0+:3];
	assign fu_crossbar__prologue_count_inport[3+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[3+:3];
	assign fu_crossbar__prologue_count_inport[0+:3] = ctrl_mem__prologue_count_outport_fu_crossbar[0+:3];
	assign to_mem_raddr__msg = element__to_mem_raddr__msg[6+:3];
	assign element__to_mem_raddr__rdy[2+:1] = to_mem_raddr__rdy;
	assign to_mem_raddr__val = element__to_mem_raddr__val[2+:1];
	assign element__from_mem_rdata__msg[70+:35] = from_mem_rdata__msg;
	assign from_mem_rdata__rdy = element__from_mem_rdata__rdy[2+:1];
	assign element__from_mem_rdata__val[2+:1] = from_mem_rdata__val;
	assign to_mem_waddr__msg = element__to_mem_waddr__msg[6+:3];
	assign element__to_mem_waddr__rdy[2+:1] = to_mem_waddr__rdy;
	assign to_mem_waddr__val = element__to_mem_waddr__val[2+:1];
	assign to_mem_wdata__msg = element__to_mem_wdata__msg[70+:35];
	assign element__to_mem_wdata__rdy[2+:1] = to_mem_wdata__rdy;
	assign to_mem_wdata__val = element__to_mem_wdata__val[2+:1];
	assign element__to_mem_raddr__rdy[1+:1] = 1'd0;
	assign element__from_mem_rdata__val[1+:1] = 1'd0;
	assign element__from_mem_rdata__msg[35+:35] = 35'h000000000;
	assign element__to_mem_waddr__rdy[1+:1] = 1'd0;
	assign element__to_mem_wdata__rdy[1+:1] = 1'd0;
	assign element__to_mem_raddr__rdy[0+:1] = 1'd0;
	assign element__from_mem_rdata__val[0+:1] = 1'd0;
	assign element__from_mem_rdata__msg[0+:35] = 35'h000000000;
	assign element__to_mem_waddr__rdy[0+:1] = 1'd0;
	assign element__to_mem_wdata__rdy[0+:1] = 1'd0;
	assign tile_in_channel__recv__msg[0] = recv_data__msg[245+:35];
	assign recv_data__rdy[7+:1] = tile_in_channel__recv__rdy[0];
	assign tile_in_channel__recv__val[0] = recv_data__val[7+:1];
	assign routing_crossbar__recv_data__msg[245+:35] = tile_in_channel__send__msg[0];
	assign tile_in_channel__send__rdy[0] = routing_crossbar__recv_data__rdy[7+:1];
	assign routing_crossbar__recv_data__val[7+:1] = tile_in_channel__send__val[0];
	assign tile_in_channel__recv__msg[1] = recv_data__msg[210+:35];
	assign recv_data__rdy[6+:1] = tile_in_channel__recv__rdy[1];
	assign tile_in_channel__recv__val[1] = recv_data__val[6+:1];
	assign routing_crossbar__recv_data__msg[210+:35] = tile_in_channel__send__msg[1];
	assign tile_in_channel__send__rdy[1] = routing_crossbar__recv_data__rdy[6+:1];
	assign routing_crossbar__recv_data__val[6+:1] = tile_in_channel__send__val[1];
	assign tile_in_channel__recv__msg[2] = recv_data__msg[175+:35];
	assign recv_data__rdy[5+:1] = tile_in_channel__recv__rdy[2];
	assign tile_in_channel__recv__val[2] = recv_data__val[5+:1];
	assign routing_crossbar__recv_data__msg[175+:35] = tile_in_channel__send__msg[2];
	assign tile_in_channel__send__rdy[2] = routing_crossbar__recv_data__rdy[5+:1];
	assign routing_crossbar__recv_data__val[5+:1] = tile_in_channel__send__val[2];
	assign tile_in_channel__recv__msg[3] = recv_data__msg[140+:35];
	assign recv_data__rdy[4+:1] = tile_in_channel__recv__rdy[3];
	assign tile_in_channel__recv__val[3] = recv_data__val[4+:1];
	assign routing_crossbar__recv_data__msg[140+:35] = tile_in_channel__send__msg[3];
	assign tile_in_channel__send__rdy[3] = routing_crossbar__recv_data__rdy[4+:1];
	assign routing_crossbar__recv_data__val[4+:1] = tile_in_channel__send__val[3];
	assign tile_in_channel__recv__msg[4] = recv_data__msg[105+:35];
	assign recv_data__rdy[3+:1] = tile_in_channel__recv__rdy[4];
	assign tile_in_channel__recv__val[4] = recv_data__val[3+:1];
	assign routing_crossbar__recv_data__msg[105+:35] = tile_in_channel__send__msg[4];
	assign tile_in_channel__send__rdy[4] = routing_crossbar__recv_data__rdy[3+:1];
	assign routing_crossbar__recv_data__val[3+:1] = tile_in_channel__send__val[4];
	assign tile_in_channel__recv__msg[5] = recv_data__msg[70+:35];
	assign recv_data__rdy[2+:1] = tile_in_channel__recv__rdy[5];
	assign tile_in_channel__recv__val[5] = recv_data__val[2+:1];
	assign routing_crossbar__recv_data__msg[70+:35] = tile_in_channel__send__msg[5];
	assign tile_in_channel__send__rdy[5] = routing_crossbar__recv_data__rdy[2+:1];
	assign routing_crossbar__recv_data__val[2+:1] = tile_in_channel__send__val[5];
	assign tile_in_channel__recv__msg[6] = recv_data__msg[35+:35];
	assign recv_data__rdy[1+:1] = tile_in_channel__recv__rdy[6];
	assign tile_in_channel__recv__val[6] = recv_data__val[1+:1];
	assign routing_crossbar__recv_data__msg[35+:35] = tile_in_channel__send__msg[6];
	assign tile_in_channel__send__rdy[6] = routing_crossbar__recv_data__rdy[1+:1];
	assign routing_crossbar__recv_data__val[1+:1] = tile_in_channel__send__val[6];
	assign tile_in_channel__recv__msg[7] = recv_data__msg[0+:35];
	assign recv_data__rdy[0+:1] = tile_in_channel__recv__rdy[7];
	assign tile_in_channel__recv__val[7] = recv_data__val[0+:1];
	assign routing_crossbar__recv_data__msg[0+:35] = tile_in_channel__send__msg[7];
	assign tile_in_channel__send__rdy[7] = routing_crossbar__recv_data__rdy[0+:1];
	assign routing_crossbar__recv_data__val[0+:1] = tile_in_channel__send__val[7];
	assign routing_crossbar__crossbar_outport[44+:4] = ctrl_mem__send_ctrl__msg[72+:4];
	assign fu_crossbar__crossbar_outport[22+:2] = ctrl_mem__send_ctrl__msg[48+:2];
	assign routing_crossbar__crossbar_outport[40+:4] = ctrl_mem__send_ctrl__msg[76+:4];
	assign fu_crossbar__crossbar_outport[20+:2] = ctrl_mem__send_ctrl__msg[50+:2];
	assign routing_crossbar__crossbar_outport[36+:4] = ctrl_mem__send_ctrl__msg[80+:4];
	assign fu_crossbar__crossbar_outport[18+:2] = ctrl_mem__send_ctrl__msg[52+:2];
	assign routing_crossbar__crossbar_outport[32+:4] = ctrl_mem__send_ctrl__msg[84+:4];
	assign fu_crossbar__crossbar_outport[16+:2] = ctrl_mem__send_ctrl__msg[54+:2];
	assign routing_crossbar__crossbar_outport[28+:4] = ctrl_mem__send_ctrl__msg[88+:4];
	assign fu_crossbar__crossbar_outport[14+:2] = ctrl_mem__send_ctrl__msg[56+:2];
	assign routing_crossbar__crossbar_outport[24+:4] = ctrl_mem__send_ctrl__msg[92+:4];
	assign fu_crossbar__crossbar_outport[12+:2] = ctrl_mem__send_ctrl__msg[58+:2];
	assign routing_crossbar__crossbar_outport[20+:4] = ctrl_mem__send_ctrl__msg[96+:4];
	assign fu_crossbar__crossbar_outport[10+:2] = ctrl_mem__send_ctrl__msg[60+:2];
	assign routing_crossbar__crossbar_outport[16+:4] = ctrl_mem__send_ctrl__msg[100+:4];
	assign fu_crossbar__crossbar_outport[8+:2] = ctrl_mem__send_ctrl__msg[62+:2];
	assign routing_crossbar__crossbar_outport[12+:4] = ctrl_mem__send_ctrl__msg[104+:4];
	assign fu_crossbar__crossbar_outport[6+:2] = ctrl_mem__send_ctrl__msg[64+:2];
	assign routing_crossbar__crossbar_outport[8+:4] = ctrl_mem__send_ctrl__msg[108+:4];
	assign fu_crossbar__crossbar_outport[4+:2] = ctrl_mem__send_ctrl__msg[66+:2];
	assign routing_crossbar__crossbar_outport[4+:4] = ctrl_mem__send_ctrl__msg[112+:4];
	assign fu_crossbar__crossbar_outport[2+:2] = ctrl_mem__send_ctrl__msg[68+:2];
	assign routing_crossbar__crossbar_outport[0+:4] = ctrl_mem__send_ctrl__msg[116+:4];
	assign fu_crossbar__crossbar_outport[0+:2] = ctrl_mem__send_ctrl__msg[70+:2];
	assign fu_crossbar__recv_data__msg[35+:35] = element__send_out__msg[35+:35];
	assign element__send_out__rdy[1+:1] = fu_crossbar__recv_data__rdy[1+:1];
	assign fu_crossbar__recv_data__val[1+:1] = element__send_out__val[1+:1];
	assign fu_crossbar__recv_data__msg[0+:35] = element__send_out__msg[0+:35];
	assign element__send_out__rdy[0+:1] = fu_crossbar__recv_data__rdy[0+:1];
	assign fu_crossbar__recv_data__val[0+:1] = element__send_out__val[0+:1];
	assign tile_out_or_link__recv_fu__msg[0] = fu_crossbar__send_data__msg[385+:35];
	assign fu_crossbar__send_data__rdy[11+:1] = tile_out_or_link__recv_fu__rdy[0];
	assign tile_out_or_link__recv_fu__val[0] = fu_crossbar__send_data__val[11+:1];
	assign tile_out_or_link__recv_xbar__msg[0] = routing_crossbar__send_data__msg[385+:35];
	assign routing_crossbar__send_data__rdy[11+:1] = tile_out_or_link__recv_xbar__rdy[0];
	assign tile_out_or_link__recv_xbar__val[0] = routing_crossbar__send_data__val[11+:1];
	assign send_data__msg[245+:35] = tile_out_or_link__send__msg[0];
	assign tile_out_or_link__send__rdy[0] = send_data__rdy[7+:1];
	assign send_data__val[7+:1] = tile_out_or_link__send__val[0];
	assign tile_out_or_link__recv_fu__msg[1] = fu_crossbar__send_data__msg[350+:35];
	assign fu_crossbar__send_data__rdy[10+:1] = tile_out_or_link__recv_fu__rdy[1];
	assign tile_out_or_link__recv_fu__val[1] = fu_crossbar__send_data__val[10+:1];
	assign tile_out_or_link__recv_xbar__msg[1] = routing_crossbar__send_data__msg[350+:35];
	assign routing_crossbar__send_data__rdy[10+:1] = tile_out_or_link__recv_xbar__rdy[1];
	assign tile_out_or_link__recv_xbar__val[1] = routing_crossbar__send_data__val[10+:1];
	assign send_data__msg[210+:35] = tile_out_or_link__send__msg[1];
	assign tile_out_or_link__send__rdy[1] = send_data__rdy[6+:1];
	assign send_data__val[6+:1] = tile_out_or_link__send__val[1];
	assign tile_out_or_link__recv_fu__msg[2] = fu_crossbar__send_data__msg[315+:35];
	assign fu_crossbar__send_data__rdy[9+:1] = tile_out_or_link__recv_fu__rdy[2];
	assign tile_out_or_link__recv_fu__val[2] = fu_crossbar__send_data__val[9+:1];
	assign tile_out_or_link__recv_xbar__msg[2] = routing_crossbar__send_data__msg[315+:35];
	assign routing_crossbar__send_data__rdy[9+:1] = tile_out_or_link__recv_xbar__rdy[2];
	assign tile_out_or_link__recv_xbar__val[2] = routing_crossbar__send_data__val[9+:1];
	assign send_data__msg[175+:35] = tile_out_or_link__send__msg[2];
	assign tile_out_or_link__send__rdy[2] = send_data__rdy[5+:1];
	assign send_data__val[5+:1] = tile_out_or_link__send__val[2];
	assign tile_out_or_link__recv_fu__msg[3] = fu_crossbar__send_data__msg[280+:35];
	assign fu_crossbar__send_data__rdy[8+:1] = tile_out_or_link__recv_fu__rdy[3];
	assign tile_out_or_link__recv_fu__val[3] = fu_crossbar__send_data__val[8+:1];
	assign tile_out_or_link__recv_xbar__msg[3] = routing_crossbar__send_data__msg[280+:35];
	assign routing_crossbar__send_data__rdy[8+:1] = tile_out_or_link__recv_xbar__rdy[3];
	assign tile_out_or_link__recv_xbar__val[3] = routing_crossbar__send_data__val[8+:1];
	assign send_data__msg[140+:35] = tile_out_or_link__send__msg[3];
	assign tile_out_or_link__send__rdy[3] = send_data__rdy[4+:1];
	assign send_data__val[4+:1] = tile_out_or_link__send__val[3];
	assign tile_out_or_link__recv_fu__msg[4] = fu_crossbar__send_data__msg[245+:35];
	assign fu_crossbar__send_data__rdy[7+:1] = tile_out_or_link__recv_fu__rdy[4];
	assign tile_out_or_link__recv_fu__val[4] = fu_crossbar__send_data__val[7+:1];
	assign tile_out_or_link__recv_xbar__msg[4] = routing_crossbar__send_data__msg[245+:35];
	assign routing_crossbar__send_data__rdy[7+:1] = tile_out_or_link__recv_xbar__rdy[4];
	assign tile_out_or_link__recv_xbar__val[4] = routing_crossbar__send_data__val[7+:1];
	assign send_data__msg[105+:35] = tile_out_or_link__send__msg[4];
	assign tile_out_or_link__send__rdy[4] = send_data__rdy[3+:1];
	assign send_data__val[3+:1] = tile_out_or_link__send__val[4];
	assign tile_out_or_link__recv_fu__msg[5] = fu_crossbar__send_data__msg[210+:35];
	assign fu_crossbar__send_data__rdy[6+:1] = tile_out_or_link__recv_fu__rdy[5];
	assign tile_out_or_link__recv_fu__val[5] = fu_crossbar__send_data__val[6+:1];
	assign tile_out_or_link__recv_xbar__msg[5] = routing_crossbar__send_data__msg[210+:35];
	assign routing_crossbar__send_data__rdy[6+:1] = tile_out_or_link__recv_xbar__rdy[5];
	assign tile_out_or_link__recv_xbar__val[5] = routing_crossbar__send_data__val[6+:1];
	assign send_data__msg[70+:35] = tile_out_or_link__send__msg[5];
	assign tile_out_or_link__send__rdy[5] = send_data__rdy[2+:1];
	assign send_data__val[2+:1] = tile_out_or_link__send__val[5];
	assign tile_out_or_link__recv_fu__msg[6] = fu_crossbar__send_data__msg[175+:35];
	assign fu_crossbar__send_data__rdy[5+:1] = tile_out_or_link__recv_fu__rdy[6];
	assign tile_out_or_link__recv_fu__val[6] = fu_crossbar__send_data__val[5+:1];
	assign tile_out_or_link__recv_xbar__msg[6] = routing_crossbar__send_data__msg[175+:35];
	assign routing_crossbar__send_data__rdy[5+:1] = tile_out_or_link__recv_xbar__rdy[6];
	assign tile_out_or_link__recv_xbar__val[6] = routing_crossbar__send_data__val[5+:1];
	assign send_data__msg[35+:35] = tile_out_or_link__send__msg[6];
	assign tile_out_or_link__send__rdy[6] = send_data__rdy[1+:1];
	assign send_data__val[1+:1] = tile_out_or_link__send__val[6];
	assign tile_out_or_link__recv_fu__msg[7] = fu_crossbar__send_data__msg[140+:35];
	assign fu_crossbar__send_data__rdy[4+:1] = tile_out_or_link__recv_fu__rdy[7];
	assign tile_out_or_link__recv_fu__val[7] = fu_crossbar__send_data__val[4+:1];
	assign tile_out_or_link__recv_xbar__msg[7] = routing_crossbar__send_data__msg[140+:35];
	assign routing_crossbar__send_data__rdy[4+:1] = tile_out_or_link__recv_xbar__rdy[7];
	assign tile_out_or_link__recv_xbar__val[7] = routing_crossbar__send_data__val[4+:1];
	assign send_data__msg[0+:35] = tile_out_or_link__send__msg[7];
	assign tile_out_or_link__send__rdy[7] = send_data__rdy[0+:1];
	assign send_data__val[0+:1] = tile_out_or_link__send__val[7];
	assign register_cluster__recv_data_from_routing_crossbar__msg[105+:35] = routing_crossbar__send_data__msg[105+:35];
	assign routing_crossbar__send_data__rdy[3+:1] = register_cluster__recv_data_from_routing_crossbar__rdy[3+:1];
	assign register_cluster__recv_data_from_routing_crossbar__val[3+:1] = routing_crossbar__send_data__val[3+:1];
	assign register_cluster__recv_data_from_fu_crossbar__msg[105+:35] = fu_crossbar__send_data__msg[105+:35];
	assign fu_crossbar__send_data__rdy[3+:1] = register_cluster__recv_data_from_fu_crossbar__rdy[3+:1];
	assign register_cluster__recv_data_from_fu_crossbar__val[3+:1] = fu_crossbar__send_data__val[3+:1];
	assign register_cluster__recv_data_from_const__msg[105+:35] = 35'h000000000;
	assign register_cluster__recv_data_from_const__val[3+:1] = 1'd0;
	assign element__recv_in__msg[105+:35] = register_cluster__send_data_to_fu__msg[105+:35];
	assign register_cluster__send_data_to_fu__rdy[3+:1] = element__recv_in__rdy[3+:1];
	assign element__recv_in__val[3+:1] = register_cluster__send_data_to_fu__val[3+:1];
	assign register_cluster__inport_opt = ctrl_mem__send_ctrl__msg;
	assign register_cluster__recv_data_from_routing_crossbar__msg[70+:35] = routing_crossbar__send_data__msg[70+:35];
	assign routing_crossbar__send_data__rdy[2+:1] = register_cluster__recv_data_from_routing_crossbar__rdy[2+:1];
	assign register_cluster__recv_data_from_routing_crossbar__val[2+:1] = routing_crossbar__send_data__val[2+:1];
	assign register_cluster__recv_data_from_fu_crossbar__msg[70+:35] = fu_crossbar__send_data__msg[70+:35];
	assign fu_crossbar__send_data__rdy[2+:1] = register_cluster__recv_data_from_fu_crossbar__rdy[2+:1];
	assign register_cluster__recv_data_from_fu_crossbar__val[2+:1] = fu_crossbar__send_data__val[2+:1];
	assign register_cluster__recv_data_from_const__msg[70+:35] = 35'h000000000;
	assign register_cluster__recv_data_from_const__val[2+:1] = 1'd0;
	assign element__recv_in__msg[70+:35] = register_cluster__send_data_to_fu__msg[70+:35];
	assign register_cluster__send_data_to_fu__rdy[2+:1] = element__recv_in__rdy[2+:1];
	assign element__recv_in__val[2+:1] = register_cluster__send_data_to_fu__val[2+:1];
	assign register_cluster__recv_data_from_routing_crossbar__msg[35+:35] = routing_crossbar__send_data__msg[35+:35];
	assign routing_crossbar__send_data__rdy[1+:1] = register_cluster__recv_data_from_routing_crossbar__rdy[1+:1];
	assign register_cluster__recv_data_from_routing_crossbar__val[1+:1] = routing_crossbar__send_data__val[1+:1];
	assign register_cluster__recv_data_from_fu_crossbar__msg[35+:35] = fu_crossbar__send_data__msg[35+:35];
	assign fu_crossbar__send_data__rdy[1+:1] = register_cluster__recv_data_from_fu_crossbar__rdy[1+:1];
	assign register_cluster__recv_data_from_fu_crossbar__val[1+:1] = fu_crossbar__send_data__val[1+:1];
	assign register_cluster__recv_data_from_const__msg[35+:35] = 35'h000000000;
	assign register_cluster__recv_data_from_const__val[1+:1] = 1'd0;
	assign element__recv_in__msg[35+:35] = register_cluster__send_data_to_fu__msg[35+:35];
	assign register_cluster__send_data_to_fu__rdy[1+:1] = element__recv_in__rdy[1+:1];
	assign element__recv_in__val[1+:1] = register_cluster__send_data_to_fu__val[1+:1];
	assign register_cluster__recv_data_from_routing_crossbar__msg[0+:35] = routing_crossbar__send_data__msg[0+:35];
	assign routing_crossbar__send_data__rdy[0+:1] = register_cluster__recv_data_from_routing_crossbar__rdy[0+:1];
	assign register_cluster__recv_data_from_routing_crossbar__val[0+:1] = routing_crossbar__send_data__val[0+:1];
	assign register_cluster__recv_data_from_fu_crossbar__msg[0+:35] = fu_crossbar__send_data__msg[0+:35];
	assign fu_crossbar__send_data__rdy[0+:1] = register_cluster__recv_data_from_fu_crossbar__rdy[0+:1];
	assign register_cluster__recv_data_from_fu_crossbar__val[0+:1] = fu_crossbar__send_data__val[0+:1];
	assign register_cluster__recv_data_from_const__msg[0+:35] = 35'h000000000;
	assign register_cluster__recv_data_from_const__val[0+:1] = 1'd0;
	assign element__recv_in__msg[0+:35] = register_cluster__send_data_to_fu__msg[0+:35];
	assign register_cluster__send_data_to_fu__rdy[0+:1] = element__recv_in__rdy[0+:1];
	assign element__recv_in__val[0+:1] = register_cluster__send_data_to_fu__val[0+:1];
endmodule
module CgraTemplateRTL (
	address_lower,
	address_upper,
	cgra_id,
	clk,
	reset,
	recv_from_cpu_pkt__msg,
	recv_from_cpu_pkt__rdy,
	recv_from_cpu_pkt__val,
	recv_from_inter_cgra_noc__msg,
	recv_from_inter_cgra_noc__rdy,
	recv_from_inter_cgra_noc__val,
	send_to_cpu_pkt__msg,
	send_to_cpu_pkt__rdy,
	send_to_cpu_pkt__val,
	send_to_inter_cgra_noc__msg,
	send_to_inter_cgra_noc__rdy,
	send_to_inter_cgra_noc__val
);
	input wire [2:0] address_lower;
	input wire [2:0] address_upper;
	input wire [1:0] cgra_id;
	input wire [0:0] clk;
	input wire [0:0] reset;
	input wire [207:0] recv_from_cpu_pkt__msg;
	output wire [0:0] recv_from_cpu_pkt__rdy;
	input wire [0:0] recv_from_cpu_pkt__val;
	input wire [208:0] recv_from_inter_cgra_noc__msg;
	output wire [0:0] recv_from_inter_cgra_noc__rdy;
	input wire [0:0] recv_from_inter_cgra_noc__val;
	output wire [207:0] send_to_cpu_pkt__msg;
	input wire [0:0] send_to_cpu_pkt__rdy;
	output wire [0:0] send_to_cpu_pkt__val;
	output wire [208:0] send_to_inter_cgra_noc__msg;
	input wire [0:0] send_to_inter_cgra_noc__rdy;
	output wire [0:0] send_to_inter_cgra_noc__val;
	wire [0:0] bypass_queue__clk;
	wire [0:0] bypass_queue__count;
	wire [0:0] bypass_queue__reset;
	wire [208:0] bypass_queue__recv__msg;
	wire [0:0] bypass_queue__recv__rdy;
	wire [0:0] bypass_queue__recv__val;
	wire [208:0] bypass_queue__send__msg;
	wire [0:0] bypass_queue__send__rdy;
	wire [0:0] bypass_queue__send__val;
	BypassQueueRTL__16564dc625bb50ae bypass_queue(
		.clk(bypass_queue__clk),
		.count(bypass_queue__count),
		.reset(bypass_queue__reset),
		.recv__msg(bypass_queue__recv__msg),
		.recv__rdy(bypass_queue__recv__rdy),
		.recv__val(bypass_queue__recv__val),
		.send__msg(bypass_queue__send__msg),
		.send__rdy(bypass_queue__send__rdy),
		.send__val(bypass_queue__send__val)
	);
	wire [1:0] controller__cgra_id;
	wire [0:0] controller__clk;
	wire [0:0] controller__reset;
	wire [207:0] controller__recv_from_cpu_pkt__msg;
	wire [0:0] controller__recv_from_cpu_pkt__rdy;
	wire [0:0] controller__recv_from_cpu_pkt__val;
	wire [207:0] controller__recv_from_ctrl_ring_pkt__msg;
	wire [0:0] controller__recv_from_ctrl_ring_pkt__rdy;
	wire [0:0] controller__recv_from_ctrl_ring_pkt__val;
	wire [208:0] controller__recv_from_inter_cgra_noc__msg;
	wire [0:0] controller__recv_from_inter_cgra_noc__rdy;
	wire [0:0] controller__recv_from_inter_cgra_noc__val;
	wire [208:0] controller__recv_from_tile_load_request_pkt__msg;
	wire [0:0] controller__recv_from_tile_load_request_pkt__rdy;
	wire [0:0] controller__recv_from_tile_load_request_pkt__val;
	wire [208:0] controller__recv_from_tile_load_response_pkt__msg;
	wire [0:0] controller__recv_from_tile_load_response_pkt__rdy;
	wire [0:0] controller__recv_from_tile_load_response_pkt__val;
	wire [208:0] controller__recv_from_tile_store_request_pkt__msg;
	wire [0:0] controller__recv_from_tile_store_request_pkt__rdy;
	wire [0:0] controller__recv_from_tile_store_request_pkt__val;
	wire [207:0] controller__send_to_cpu_pkt__msg;
	wire [0:0] controller__send_to_cpu_pkt__rdy;
	wire [0:0] controller__send_to_cpu_pkt__val;
	wire [207:0] controller__send_to_ctrl_ring_pkt__msg;
	wire [0:0] controller__send_to_ctrl_ring_pkt__rdy;
	wire [0:0] controller__send_to_ctrl_ring_pkt__val;
	wire [208:0] controller__send_to_inter_cgra_noc__msg;
	wire [0:0] controller__send_to_inter_cgra_noc__rdy;
	wire [0:0] controller__send_to_inter_cgra_noc__val;
	wire [208:0] controller__send_to_mem_load_request__msg;
	wire [0:0] controller__send_to_mem_load_request__rdy;
	wire [0:0] controller__send_to_mem_load_request__val;
	wire [208:0] controller__send_to_mem_store_request__msg;
	wire [0:0] controller__send_to_mem_store_request__rdy;
	wire [0:0] controller__send_to_mem_store_request__val;
	wire [208:0] controller__send_to_tile_load_response__msg;
	wire [0:0] controller__send_to_tile_load_response__rdy;
	wire [0:0] controller__send_to_tile_load_response__val;
	ControllerRTL__8a6408c51f9d4265 controller(
		.cgra_id(controller__cgra_id),
		.clk(controller__clk),
		.reset(controller__reset),
		.recv_from_cpu_pkt__msg(controller__recv_from_cpu_pkt__msg),
		.recv_from_cpu_pkt__rdy(controller__recv_from_cpu_pkt__rdy),
		.recv_from_cpu_pkt__val(controller__recv_from_cpu_pkt__val),
		.recv_from_ctrl_ring_pkt__msg(controller__recv_from_ctrl_ring_pkt__msg),
		.recv_from_ctrl_ring_pkt__rdy(controller__recv_from_ctrl_ring_pkt__rdy),
		.recv_from_ctrl_ring_pkt__val(controller__recv_from_ctrl_ring_pkt__val),
		.recv_from_inter_cgra_noc__msg(controller__recv_from_inter_cgra_noc__msg),
		.recv_from_inter_cgra_noc__rdy(controller__recv_from_inter_cgra_noc__rdy),
		.recv_from_inter_cgra_noc__val(controller__recv_from_inter_cgra_noc__val),
		.recv_from_tile_load_request_pkt__msg(controller__recv_from_tile_load_request_pkt__msg),
		.recv_from_tile_load_request_pkt__rdy(controller__recv_from_tile_load_request_pkt__rdy),
		.recv_from_tile_load_request_pkt__val(controller__recv_from_tile_load_request_pkt__val),
		.recv_from_tile_load_response_pkt__msg(controller__recv_from_tile_load_response_pkt__msg),
		.recv_from_tile_load_response_pkt__rdy(controller__recv_from_tile_load_response_pkt__rdy),
		.recv_from_tile_load_response_pkt__val(controller__recv_from_tile_load_response_pkt__val),
		.recv_from_tile_store_request_pkt__msg(controller__recv_from_tile_store_request_pkt__msg),
		.recv_from_tile_store_request_pkt__rdy(controller__recv_from_tile_store_request_pkt__rdy),
		.recv_from_tile_store_request_pkt__val(controller__recv_from_tile_store_request_pkt__val),
		.send_to_cpu_pkt__msg(controller__send_to_cpu_pkt__msg),
		.send_to_cpu_pkt__rdy(controller__send_to_cpu_pkt__rdy),
		.send_to_cpu_pkt__val(controller__send_to_cpu_pkt__val),
		.send_to_ctrl_ring_pkt__msg(controller__send_to_ctrl_ring_pkt__msg),
		.send_to_ctrl_ring_pkt__rdy(controller__send_to_ctrl_ring_pkt__rdy),
		.send_to_ctrl_ring_pkt__val(controller__send_to_ctrl_ring_pkt__val),
		.send_to_inter_cgra_noc__msg(controller__send_to_inter_cgra_noc__msg),
		.send_to_inter_cgra_noc__rdy(controller__send_to_inter_cgra_noc__rdy),
		.send_to_inter_cgra_noc__val(controller__send_to_inter_cgra_noc__val),
		.send_to_mem_load_request__msg(controller__send_to_mem_load_request__msg),
		.send_to_mem_load_request__rdy(controller__send_to_mem_load_request__rdy),
		.send_to_mem_load_request__val(controller__send_to_mem_load_request__val),
		.send_to_mem_store_request__msg(controller__send_to_mem_store_request__msg),
		.send_to_mem_store_request__rdy(controller__send_to_mem_store_request__rdy),
		.send_to_mem_store_request__val(controller__send_to_mem_store_request__val),
		.send_to_tile_load_response__msg(controller__send_to_tile_load_response__msg),
		.send_to_tile_load_response__rdy(controller__send_to_tile_load_response__rdy),
		.send_to_tile_load_response__val(controller__send_to_tile_load_response__val)
	);
	wire [0:0] ctrl_ring__clk;
	wire [0:0] ctrl_ring__reset;
	wire [1039:0] ctrl_ring__recv__msg;
	wire [4:0] ctrl_ring__recv__rdy;
	wire [4:0] ctrl_ring__recv__val;
	wire [1039:0] ctrl_ring__send__msg;
	wire [4:0] ctrl_ring__send__rdy;
	wire [4:0] ctrl_ring__send__val;
	RingNetworkRTL__79999f3d23637960 ctrl_ring(
		.clk(ctrl_ring__clk),
		.reset(ctrl_ring__reset),
		.recv__msg(ctrl_ring__recv__msg),
		.recv__rdy(ctrl_ring__recv__rdy),
		.recv__val(ctrl_ring__recv__val),
		.send__msg(ctrl_ring__send__msg),
		.send__rdy(ctrl_ring__send__rdy),
		.send__val(ctrl_ring__send__val)
	);
	wire [2:0] data_mem__address_lower;
	wire [2:0] data_mem__address_upper;
	wire [1:0] data_mem__cgra_id;
	wire [0:0] data_mem__clk;
	wire [0:0] data_mem__reset;
	wire [208:0] data_mem__recv_from_noc_load_request__msg;
	wire [0:0] data_mem__recv_from_noc_load_request__rdy;
	wire [0:0] data_mem__recv_from_noc_load_request__val;
	wire [208:0] data_mem__recv_from_noc_load_response_pkt__msg;
	wire [0:0] data_mem__recv_from_noc_load_response_pkt__rdy;
	wire [0:0] data_mem__recv_from_noc_load_response_pkt__val;
	wire [208:0] data_mem__recv_from_noc_store_request__msg;
	wire [0:0] data_mem__recv_from_noc_store_request__rdy;
	wire [0:0] data_mem__recv_from_noc_store_request__val;
	wire [5:0] data_mem__recv_raddr__msg;
	wire [1:0] data_mem__recv_raddr__rdy;
	wire [1:0] data_mem__recv_raddr__val;
	wire [5:0] data_mem__recv_waddr__msg;
	wire [1:0] data_mem__recv_waddr__rdy;
	wire [1:0] data_mem__recv_waddr__val;
	wire [69:0] data_mem__recv_wdata__msg;
	wire [1:0] data_mem__recv_wdata__rdy;
	wire [1:0] data_mem__recv_wdata__val;
	wire [69:0] data_mem__send_rdata__msg;
	wire [1:0] data_mem__send_rdata__rdy;
	wire [1:0] data_mem__send_rdata__val;
	wire [208:0] data_mem__send_to_noc_load_request_pkt__msg;
	wire [0:0] data_mem__send_to_noc_load_request_pkt__rdy;
	wire [0:0] data_mem__send_to_noc_load_request_pkt__val;
	wire [208:0] data_mem__send_to_noc_load_response_pkt__msg;
	wire [0:0] data_mem__send_to_noc_load_response_pkt__rdy;
	wire [0:0] data_mem__send_to_noc_load_response_pkt__val;
	wire [208:0] data_mem__send_to_noc_store_pkt__msg;
	wire [0:0] data_mem__send_to_noc_store_pkt__rdy;
	wire [0:0] data_mem__send_to_noc_store_pkt__val;
	DataMemWithCrossbarRTL__e50b5d913fef7b11 data_mem(
		.address_lower(data_mem__address_lower),
		.address_upper(data_mem__address_upper),
		.cgra_id(data_mem__cgra_id),
		.clk(data_mem__clk),
		.reset(data_mem__reset),
		.recv_from_noc_load_request__msg(data_mem__recv_from_noc_load_request__msg),
		.recv_from_noc_load_request__rdy(data_mem__recv_from_noc_load_request__rdy),
		.recv_from_noc_load_request__val(data_mem__recv_from_noc_load_request__val),
		.recv_from_noc_load_response_pkt__msg(data_mem__recv_from_noc_load_response_pkt__msg),
		.recv_from_noc_load_response_pkt__rdy(data_mem__recv_from_noc_load_response_pkt__rdy),
		.recv_from_noc_load_response_pkt__val(data_mem__recv_from_noc_load_response_pkt__val),
		.recv_from_noc_store_request__msg(data_mem__recv_from_noc_store_request__msg),
		.recv_from_noc_store_request__rdy(data_mem__recv_from_noc_store_request__rdy),
		.recv_from_noc_store_request__val(data_mem__recv_from_noc_store_request__val),
		.recv_raddr__msg(data_mem__recv_raddr__msg),
		.recv_raddr__rdy(data_mem__recv_raddr__rdy),
		.recv_raddr__val(data_mem__recv_raddr__val),
		.recv_waddr__msg(data_mem__recv_waddr__msg),
		.recv_waddr__rdy(data_mem__recv_waddr__rdy),
		.recv_waddr__val(data_mem__recv_waddr__val),
		.recv_wdata__msg(data_mem__recv_wdata__msg),
		.recv_wdata__rdy(data_mem__recv_wdata__rdy),
		.recv_wdata__val(data_mem__recv_wdata__val),
		.send_rdata__msg(data_mem__send_rdata__msg),
		.send_rdata__rdy(data_mem__send_rdata__rdy),
		.send_rdata__val(data_mem__send_rdata__val),
		.send_to_noc_load_request_pkt__msg(data_mem__send_to_noc_load_request_pkt__msg),
		.send_to_noc_load_request_pkt__rdy(data_mem__send_to_noc_load_request_pkt__rdy),
		.send_to_noc_load_request_pkt__val(data_mem__send_to_noc_load_request_pkt__val),
		.send_to_noc_load_response_pkt__msg(data_mem__send_to_noc_load_response_pkt__msg),
		.send_to_noc_load_response_pkt__rdy(data_mem__send_to_noc_load_response_pkt__rdy),
		.send_to_noc_load_response_pkt__val(data_mem__send_to_noc_load_response_pkt__val),
		.send_to_noc_store_pkt__msg(data_mem__send_to_noc_store_pkt__msg),
		.send_to_noc_store_pkt__rdy(data_mem__send_to_noc_store_pkt__rdy),
		.send_to_noc_store_pkt__val(data_mem__send_to_noc_store_pkt__val)
	);
	wire [1:0] tile__cgra_id [0:3];
	wire [0:0] tile__clk [0:3];
	wire [0:0] tile__reset [0:3];
	wire [2:0] tile__tile_id [0:3];
	wire [34:0] tile__from_mem_rdata__msg [0:3];
	wire [0:0] tile__from_mem_rdata__rdy [0:3];
	wire [0:0] tile__from_mem_rdata__val [0:3];
	wire [279:0] tile__recv_data__msg [0:3];
	wire [7:0] tile__recv_data__rdy [0:3];
	wire [7:0] tile__recv_data__val [0:3];
	wire [207:0] tile__recv_from_controller_pkt__msg [0:3];
	wire [0:0] tile__recv_from_controller_pkt__rdy [0:3];
	wire [0:0] tile__recv_from_controller_pkt__val [0:3];
	wire [279:0] tile__send_data__msg [0:3];
	wire [7:0] tile__send_data__rdy [0:3];
	wire [7:0] tile__send_data__val [0:3];
	wire [207:0] tile__send_to_controller_pkt__msg [0:3];
	wire [0:0] tile__send_to_controller_pkt__rdy [0:3];
	wire [0:0] tile__send_to_controller_pkt__val [0:3];
	wire [2:0] tile__to_mem_raddr__msg [0:3];
	wire [0:0] tile__to_mem_raddr__rdy [0:3];
	wire [0:0] tile__to_mem_raddr__val [0:3];
	wire [2:0] tile__to_mem_waddr__msg [0:3];
	wire [0:0] tile__to_mem_waddr__rdy [0:3];
	wire [0:0] tile__to_mem_waddr__val [0:3];
	wire [34:0] tile__to_mem_wdata__msg [0:3];
	wire [0:0] tile__to_mem_wdata__rdy [0:3];
	wire [0:0] tile__to_mem_wdata__val [0:3];
	TileRTL__5c45db0fc5682835 tile__0(
		.cgra_id(tile__cgra_id[0]),
		.clk(tile__clk[0]),
		.reset(tile__reset[0]),
		.tile_id(tile__tile_id[0]),
		.from_mem_rdata__msg(tile__from_mem_rdata__msg[0]),
		.from_mem_rdata__rdy(tile__from_mem_rdata__rdy[0]),
		.from_mem_rdata__val(tile__from_mem_rdata__val[0]),
		.recv_data__msg(tile__recv_data__msg[0]),
		.recv_data__rdy(tile__recv_data__rdy[0]),
		.recv_data__val(tile__recv_data__val[0]),
		.recv_from_controller_pkt__msg(tile__recv_from_controller_pkt__msg[0]),
		.recv_from_controller_pkt__rdy(tile__recv_from_controller_pkt__rdy[0]),
		.recv_from_controller_pkt__val(tile__recv_from_controller_pkt__val[0]),
		.send_data__msg(tile__send_data__msg[0]),
		.send_data__rdy(tile__send_data__rdy[0]),
		.send_data__val(tile__send_data__val[0]),
		.send_to_controller_pkt__msg(tile__send_to_controller_pkt__msg[0]),
		.send_to_controller_pkt__rdy(tile__send_to_controller_pkt__rdy[0]),
		.send_to_controller_pkt__val(tile__send_to_controller_pkt__val[0]),
		.to_mem_raddr__msg(tile__to_mem_raddr__msg[0]),
		.to_mem_raddr__rdy(tile__to_mem_raddr__rdy[0]),
		.to_mem_raddr__val(tile__to_mem_raddr__val[0]),
		.to_mem_waddr__msg(tile__to_mem_waddr__msg[0]),
		.to_mem_waddr__rdy(tile__to_mem_waddr__rdy[0]),
		.to_mem_waddr__val(tile__to_mem_waddr__val[0]),
		.to_mem_wdata__msg(tile__to_mem_wdata__msg[0]),
		.to_mem_wdata__rdy(tile__to_mem_wdata__rdy[0]),
		.to_mem_wdata__val(tile__to_mem_wdata__val[0])
	);
	TileRTL__5c45db0fc5682835 tile__1(
		.cgra_id(tile__cgra_id[1]),
		.clk(tile__clk[1]),
		.reset(tile__reset[1]),
		.tile_id(tile__tile_id[1]),
		.from_mem_rdata__msg(tile__from_mem_rdata__msg[1]),
		.from_mem_rdata__rdy(tile__from_mem_rdata__rdy[1]),
		.from_mem_rdata__val(tile__from_mem_rdata__val[1]),
		.recv_data__msg(tile__recv_data__msg[1]),
		.recv_data__rdy(tile__recv_data__rdy[1]),
		.recv_data__val(tile__recv_data__val[1]),
		.recv_from_controller_pkt__msg(tile__recv_from_controller_pkt__msg[1]),
		.recv_from_controller_pkt__rdy(tile__recv_from_controller_pkt__rdy[1]),
		.recv_from_controller_pkt__val(tile__recv_from_controller_pkt__val[1]),
		.send_data__msg(tile__send_data__msg[1]),
		.send_data__rdy(tile__send_data__rdy[1]),
		.send_data__val(tile__send_data__val[1]),
		.send_to_controller_pkt__msg(tile__send_to_controller_pkt__msg[1]),
		.send_to_controller_pkt__rdy(tile__send_to_controller_pkt__rdy[1]),
		.send_to_controller_pkt__val(tile__send_to_controller_pkt__val[1]),
		.to_mem_raddr__msg(tile__to_mem_raddr__msg[1]),
		.to_mem_raddr__rdy(tile__to_mem_raddr__rdy[1]),
		.to_mem_raddr__val(tile__to_mem_raddr__val[1]),
		.to_mem_waddr__msg(tile__to_mem_waddr__msg[1]),
		.to_mem_waddr__rdy(tile__to_mem_waddr__rdy[1]),
		.to_mem_waddr__val(tile__to_mem_waddr__val[1]),
		.to_mem_wdata__msg(tile__to_mem_wdata__msg[1]),
		.to_mem_wdata__rdy(tile__to_mem_wdata__rdy[1]),
		.to_mem_wdata__val(tile__to_mem_wdata__val[1])
	);
	TileRTL__5c45db0fc5682835 tile__2(
		.cgra_id(tile__cgra_id[2]),
		.clk(tile__clk[2]),
		.reset(tile__reset[2]),
		.tile_id(tile__tile_id[2]),
		.from_mem_rdata__msg(tile__from_mem_rdata__msg[2]),
		.from_mem_rdata__rdy(tile__from_mem_rdata__rdy[2]),
		.from_mem_rdata__val(tile__from_mem_rdata__val[2]),
		.recv_data__msg(tile__recv_data__msg[2]),
		.recv_data__rdy(tile__recv_data__rdy[2]),
		.recv_data__val(tile__recv_data__val[2]),
		.recv_from_controller_pkt__msg(tile__recv_from_controller_pkt__msg[2]),
		.recv_from_controller_pkt__rdy(tile__recv_from_controller_pkt__rdy[2]),
		.recv_from_controller_pkt__val(tile__recv_from_controller_pkt__val[2]),
		.send_data__msg(tile__send_data__msg[2]),
		.send_data__rdy(tile__send_data__rdy[2]),
		.send_data__val(tile__send_data__val[2]),
		.send_to_controller_pkt__msg(tile__send_to_controller_pkt__msg[2]),
		.send_to_controller_pkt__rdy(tile__send_to_controller_pkt__rdy[2]),
		.send_to_controller_pkt__val(tile__send_to_controller_pkt__val[2]),
		.to_mem_raddr__msg(tile__to_mem_raddr__msg[2]),
		.to_mem_raddr__rdy(tile__to_mem_raddr__rdy[2]),
		.to_mem_raddr__val(tile__to_mem_raddr__val[2]),
		.to_mem_waddr__msg(tile__to_mem_waddr__msg[2]),
		.to_mem_waddr__rdy(tile__to_mem_waddr__rdy[2]),
		.to_mem_waddr__val(tile__to_mem_waddr__val[2]),
		.to_mem_wdata__msg(tile__to_mem_wdata__msg[2]),
		.to_mem_wdata__rdy(tile__to_mem_wdata__rdy[2]),
		.to_mem_wdata__val(tile__to_mem_wdata__val[2])
	);
	TileRTL__5c45db0fc5682835 tile__3(
		.cgra_id(tile__cgra_id[3]),
		.clk(tile__clk[3]),
		.reset(tile__reset[3]),
		.tile_id(tile__tile_id[3]),
		.from_mem_rdata__msg(tile__from_mem_rdata__msg[3]),
		.from_mem_rdata__rdy(tile__from_mem_rdata__rdy[3]),
		.from_mem_rdata__val(tile__from_mem_rdata__val[3]),
		.recv_data__msg(tile__recv_data__msg[3]),
		.recv_data__rdy(tile__recv_data__rdy[3]),
		.recv_data__val(tile__recv_data__val[3]),
		.recv_from_controller_pkt__msg(tile__recv_from_controller_pkt__msg[3]),
		.recv_from_controller_pkt__rdy(tile__recv_from_controller_pkt__rdy[3]),
		.recv_from_controller_pkt__val(tile__recv_from_controller_pkt__val[3]),
		.send_data__msg(tile__send_data__msg[3]),
		.send_data__rdy(tile__send_data__rdy[3]),
		.send_data__val(tile__send_data__val[3]),
		.send_to_controller_pkt__msg(tile__send_to_controller_pkt__msg[3]),
		.send_to_controller_pkt__rdy(tile__send_to_controller_pkt__rdy[3]),
		.send_to_controller_pkt__val(tile__send_to_controller_pkt__val[3]),
		.to_mem_raddr__msg(tile__to_mem_raddr__msg[3]),
		.to_mem_raddr__rdy(tile__to_mem_raddr__rdy[3]),
		.to_mem_raddr__val(tile__to_mem_raddr__val[3]),
		.to_mem_waddr__msg(tile__to_mem_waddr__msg[3]),
		.to_mem_waddr__rdy(tile__to_mem_waddr__rdy[3]),
		.to_mem_waddr__val(tile__to_mem_waddr__val[3]),
		.to_mem_wdata__msg(tile__to_mem_wdata__msg[3]),
		.to_mem_wdata__rdy(tile__to_mem_wdata__rdy[3]),
		.to_mem_wdata__val(tile__to_mem_wdata__val[3])
	);
	assign tile__clk[0] = clk;
	assign tile__reset[0] = reset;
	assign tile__clk[1] = clk;
	assign tile__reset[1] = reset;
	assign tile__clk[2] = clk;
	assign tile__reset[2] = reset;
	assign tile__clk[3] = clk;
	assign tile__reset[3] = reset;
	assign data_mem__clk = clk;
	assign data_mem__reset = reset;
	assign controller__clk = clk;
	assign controller__reset = reset;
	assign ctrl_ring__clk = clk;
	assign ctrl_ring__reset = reset;
	assign controller__cgra_id = cgra_id;
	assign data_mem__cgra_id = cgra_id;
	assign data_mem__address_lower = address_lower;
	assign data_mem__address_upper = address_upper;
	assign data_mem__recv_from_noc_load_request__msg = controller__send_to_mem_load_request__msg;
	assign controller__send_to_mem_load_request__rdy = data_mem__recv_from_noc_load_request__rdy;
	assign data_mem__recv_from_noc_load_request__val = controller__send_to_mem_load_request__val;
	assign data_mem__recv_from_noc_store_request__msg = controller__send_to_mem_store_request__msg;
	assign controller__send_to_mem_store_request__rdy = data_mem__recv_from_noc_store_request__rdy;
	assign data_mem__recv_from_noc_store_request__val = controller__send_to_mem_store_request__val;
	assign data_mem__recv_from_noc_load_response_pkt__msg = controller__send_to_tile_load_response__msg;
	assign controller__send_to_tile_load_response__rdy = data_mem__recv_from_noc_load_response_pkt__rdy;
	assign data_mem__recv_from_noc_load_response_pkt__val = controller__send_to_tile_load_response__val;
	assign controller__recv_from_tile_load_request_pkt__msg = data_mem__send_to_noc_load_request_pkt__msg;
	assign data_mem__send_to_noc_load_request_pkt__rdy = controller__recv_from_tile_load_request_pkt__rdy;
	assign controller__recv_from_tile_load_request_pkt__val = data_mem__send_to_noc_load_request_pkt__val;
	assign controller__recv_from_tile_load_response_pkt__msg = data_mem__send_to_noc_load_response_pkt__msg;
	assign data_mem__send_to_noc_load_response_pkt__rdy = controller__recv_from_tile_load_response_pkt__rdy;
	assign controller__recv_from_tile_load_response_pkt__val = data_mem__send_to_noc_load_response_pkt__val;
	assign controller__recv_from_tile_store_request_pkt__msg = data_mem__send_to_noc_store_pkt__msg;
	assign data_mem__send_to_noc_store_pkt__rdy = controller__recv_from_tile_store_request_pkt__rdy;
	assign controller__recv_from_tile_store_request_pkt__val = data_mem__send_to_noc_store_pkt__val;
	assign bypass_queue__clk = clk;
	assign bypass_queue__reset = reset;
	assign controller__recv_from_inter_cgra_noc__msg = bypass_queue__send__msg;
	assign bypass_queue__send__rdy = controller__recv_from_inter_cgra_noc__rdy;
	assign controller__recv_from_inter_cgra_noc__val = bypass_queue__send__val;
	assign bypass_queue__recv__msg = controller__send_to_inter_cgra_noc__msg;
	assign controller__send_to_inter_cgra_noc__rdy = bypass_queue__recv__rdy;
	assign bypass_queue__recv__val = controller__send_to_inter_cgra_noc__val;
	assign controller__recv_from_cpu_pkt__msg = recv_from_cpu_pkt__msg;
	assign recv_from_cpu_pkt__rdy = controller__recv_from_cpu_pkt__rdy;
	assign controller__recv_from_cpu_pkt__val = recv_from_cpu_pkt__val;
	assign send_to_cpu_pkt__msg = controller__send_to_cpu_pkt__msg;
	assign controller__send_to_cpu_pkt__rdy = send_to_cpu_pkt__rdy;
	assign send_to_cpu_pkt__val = controller__send_to_cpu_pkt__val;
	assign tile__cgra_id[0] = cgra_id;
	assign tile__tile_id[0] = 3'd0;
	assign tile__cgra_id[1] = cgra_id;
	assign tile__tile_id[1] = 3'd1;
	assign tile__cgra_id[2] = cgra_id;
	assign tile__tile_id[2] = 3'd2;
	assign tile__cgra_id[3] = cgra_id;
	assign tile__tile_id[3] = 3'd3;
	assign tile__recv_from_controller_pkt__msg[0] = ctrl_ring__send__msg[832+:208];
	assign ctrl_ring__send__rdy[4+:1] = tile__recv_from_controller_pkt__rdy[0];
	assign tile__recv_from_controller_pkt__val[0] = ctrl_ring__send__val[4+:1];
	assign tile__recv_from_controller_pkt__msg[1] = ctrl_ring__send__msg[624+:208];
	assign ctrl_ring__send__rdy[3+:1] = tile__recv_from_controller_pkt__rdy[1];
	assign tile__recv_from_controller_pkt__val[1] = ctrl_ring__send__val[3+:1];
	assign tile__recv_from_controller_pkt__msg[2] = ctrl_ring__send__msg[416+:208];
	assign ctrl_ring__send__rdy[2+:1] = tile__recv_from_controller_pkt__rdy[2];
	assign tile__recv_from_controller_pkt__val[2] = ctrl_ring__send__val[2+:1];
	assign tile__recv_from_controller_pkt__msg[3] = ctrl_ring__send__msg[208+:208];
	assign ctrl_ring__send__rdy[1+:1] = tile__recv_from_controller_pkt__rdy[3];
	assign tile__recv_from_controller_pkt__val[3] = ctrl_ring__send__val[1+:1];
	assign controller__recv_from_ctrl_ring_pkt__msg = ctrl_ring__send__msg[0+:208];
	assign ctrl_ring__send__rdy[0+:1] = controller__recv_from_ctrl_ring_pkt__rdy;
	assign controller__recv_from_ctrl_ring_pkt__val = ctrl_ring__send__val[0+:1];
	assign ctrl_ring__recv__msg[832+:208] = tile__send_to_controller_pkt__msg[0];
	assign tile__send_to_controller_pkt__rdy[0] = ctrl_ring__recv__rdy[4+:1];
	assign ctrl_ring__recv__val[4+:1] = tile__send_to_controller_pkt__val[0];
	assign ctrl_ring__recv__msg[624+:208] = tile__send_to_controller_pkt__msg[1];
	assign tile__send_to_controller_pkt__rdy[1] = ctrl_ring__recv__rdy[3+:1];
	assign ctrl_ring__recv__val[3+:1] = tile__send_to_controller_pkt__val[1];
	assign ctrl_ring__recv__msg[416+:208] = tile__send_to_controller_pkt__msg[2];
	assign tile__send_to_controller_pkt__rdy[2] = ctrl_ring__recv__rdy[2+:1];
	assign ctrl_ring__recv__val[2+:1] = tile__send_to_controller_pkt__val[2];
	assign ctrl_ring__recv__msg[208+:208] = tile__send_to_controller_pkt__msg[3];
	assign tile__send_to_controller_pkt__rdy[3] = ctrl_ring__recv__rdy[1+:1];
	assign ctrl_ring__recv__val[1+:1] = tile__send_to_controller_pkt__val[3];
	assign ctrl_ring__recv__msg[0+:208] = controller__send_to_ctrl_ring_pkt__msg;
	assign controller__send_to_ctrl_ring_pkt__rdy = ctrl_ring__recv__rdy[0+:1];
	assign ctrl_ring__recv__val[0+:1] = controller__send_to_ctrl_ring_pkt__val;
	assign data_mem__recv_raddr__msg[3+:3] = tile__to_mem_raddr__msg[0];
	assign tile__to_mem_raddr__rdy[0] = data_mem__recv_raddr__rdy[1+:1];
	assign data_mem__recv_raddr__val[1+:1] = tile__to_mem_raddr__val[0];
	assign tile__from_mem_rdata__msg[0] = data_mem__send_rdata__msg[35+:35];
	assign data_mem__send_rdata__rdy[1+:1] = tile__from_mem_rdata__rdy[0];
	assign tile__from_mem_rdata__val[0] = data_mem__send_rdata__val[1+:1];
	assign data_mem__recv_waddr__msg[3+:3] = tile__to_mem_waddr__msg[0];
	assign tile__to_mem_waddr__rdy[0] = data_mem__recv_waddr__rdy[1+:1];
	assign data_mem__recv_waddr__val[1+:1] = tile__to_mem_waddr__val[0];
	assign data_mem__recv_wdata__msg[35+:35] = tile__to_mem_wdata__msg[0];
	assign tile__to_mem_wdata__rdy[0] = data_mem__recv_wdata__rdy[1+:1];
	assign data_mem__recv_wdata__val[1+:1] = tile__to_mem_wdata__val[0];
	assign data_mem__recv_raddr__msg[0+:3] = tile__to_mem_raddr__msg[2];
	assign tile__to_mem_raddr__rdy[2] = data_mem__recv_raddr__rdy[0+:1];
	assign data_mem__recv_raddr__val[0+:1] = tile__to_mem_raddr__val[2];
	assign tile__from_mem_rdata__msg[2] = data_mem__send_rdata__msg[0+:35];
	assign data_mem__send_rdata__rdy[0+:1] = tile__from_mem_rdata__rdy[2];
	assign tile__from_mem_rdata__val[2] = data_mem__send_rdata__val[0+:1];
	assign data_mem__recv_waddr__msg[0+:3] = tile__to_mem_waddr__msg[2];
	assign tile__to_mem_waddr__rdy[2] = data_mem__recv_waddr__rdy[0+:1];
	assign data_mem__recv_waddr__val[0+:1] = tile__to_mem_waddr__val[2];
	assign data_mem__recv_wdata__msg[0+:35] = tile__to_mem_wdata__msg[2];
	assign tile__to_mem_wdata__rdy[2] = data_mem__recv_wdata__rdy[0+:1];
	assign data_mem__recv_wdata__val[0+:1] = tile__to_mem_wdata__val[2];
	assign tile__recv_data__msg[1][175+:35] = tile__send_data__msg[0][140+:35];
	assign tile__send_data__rdy[0][4+:1] = tile__recv_data__rdy[1][5+:1];
	assign tile__recv_data__val[1][5+:1] = tile__send_data__val[0][4+:1];
	assign tile__recv_data__msg[0][140+:35] = tile__send_data__msg[1][175+:35];
	assign tile__send_data__rdy[1][5+:1] = tile__recv_data__rdy[0][4+:1];
	assign tile__recv_data__val[0][4+:1] = tile__send_data__val[1][5+:1];
	assign tile__recv_data__msg[3][175+:35] = tile__send_data__msg[2][140+:35];
	assign tile__send_data__rdy[2][4+:1] = tile__recv_data__rdy[3][5+:1];
	assign tile__recv_data__val[3][5+:1] = tile__send_data__val[2][4+:1];
	assign tile__recv_data__msg[2][140+:35] = tile__send_data__msg[3][175+:35];
	assign tile__send_data__rdy[3][5+:1] = tile__recv_data__rdy[2][4+:1];
	assign tile__recv_data__val[2][4+:1] = tile__send_data__val[3][5+:1];
	assign tile__recv_data__msg[2][210+:35] = tile__send_data__msg[0][245+:35];
	assign tile__send_data__rdy[0][7+:1] = tile__recv_data__rdy[2][6+:1];
	assign tile__recv_data__val[2][6+:1] = tile__send_data__val[0][7+:1];
	assign tile__recv_data__msg[0][245+:35] = tile__send_data__msg[2][210+:35];
	assign tile__send_data__rdy[2][6+:1] = tile__recv_data__rdy[0][7+:1];
	assign tile__recv_data__val[0][7+:1] = tile__send_data__val[2][6+:1];
	assign tile__recv_data__msg[3][210+:35] = tile__send_data__msg[1][245+:35];
	assign tile__send_data__rdy[1][7+:1] = tile__recv_data__rdy[3][6+:1];
	assign tile__recv_data__val[3][6+:1] = tile__send_data__val[1][7+:1];
	assign tile__recv_data__msg[1][245+:35] = tile__send_data__msg[3][210+:35];
	assign tile__send_data__rdy[3][6+:1] = tile__recv_data__rdy[1][7+:1];
	assign tile__recv_data__val[1][7+:1] = tile__send_data__val[3][6+:1];
	assign tile__recv_data__msg[3][0+:35] = tile__send_data__msg[0][70+:35];
	assign tile__send_data__rdy[0][2+:1] = tile__recv_data__rdy[3][0+:1];
	assign tile__recv_data__val[3][0+:1] = tile__send_data__val[0][2+:1];
	assign tile__recv_data__msg[0][70+:35] = tile__send_data__msg[3][0+:35];
	assign tile__send_data__rdy[3][0+:1] = tile__recv_data__rdy[0][2+:1];
	assign tile__recv_data__val[0][2+:1] = tile__send_data__val[3][0+:1];
	assign tile__recv_data__msg[2][35+:35] = tile__send_data__msg[1][105+:35];
	assign tile__send_data__rdy[1][3+:1] = tile__recv_data__rdy[2][1+:1];
	assign tile__recv_data__val[2][1+:1] = tile__send_data__val[1][3+:1];
	assign tile__recv_data__msg[1][105+:35] = tile__send_data__msg[2][35+:35];
	assign tile__send_data__rdy[2][1+:1] = tile__recv_data__rdy[1][3+:1];
	assign tile__recv_data__val[1][3+:1] = tile__send_data__val[2][1+:1];
	assign tile__recv_data__val[0][6+:1] = 1'd0;
	assign tile__recv_data__msg[0][210+:35] = 35'h000000000;
	assign tile__recv_data__val[0][5+:1] = 1'd0;
	assign tile__recv_data__msg[0][175+:35] = 35'h000000000;
	assign tile__recv_data__val[0][3+:1] = 1'd0;
	assign tile__recv_data__msg[0][105+:35] = 35'h000000000;
	assign tile__recv_data__val[0][1+:1] = 1'd0;
	assign tile__recv_data__msg[0][35+:35] = 35'h000000000;
	assign tile__recv_data__val[0][0+:1] = 1'd0;
	assign tile__recv_data__msg[0][0+:35] = 35'h000000000;
	assign tile__send_data__rdy[0][6+:1] = 1'd0;
	assign tile__send_data__rdy[0][5+:1] = 1'd0;
	assign tile__send_data__rdy[0][3+:1] = 1'd0;
	assign tile__send_data__rdy[0][1+:1] = 1'd0;
	assign tile__send_data__rdy[0][0+:1] = 1'd0;
	assign tile__recv_data__val[1][6+:1] = 1'd0;
	assign tile__recv_data__msg[1][210+:35] = 35'h000000000;
	assign tile__recv_data__val[1][4+:1] = 1'd0;
	assign tile__recv_data__msg[1][140+:35] = 35'h000000000;
	assign tile__recv_data__val[1][2+:1] = 1'd0;
	assign tile__recv_data__msg[1][70+:35] = 35'h000000000;
	assign tile__recv_data__val[1][1+:1] = 1'd0;
	assign tile__recv_data__msg[1][35+:35] = 35'h000000000;
	assign tile__recv_data__val[1][0+:1] = 1'd0;
	assign tile__recv_data__msg[1][0+:35] = 35'h000000000;
	assign tile__send_data__rdy[1][6+:1] = 1'd0;
	assign tile__send_data__rdy[1][4+:1] = 1'd0;
	assign tile__send_data__rdy[1][2+:1] = 1'd0;
	assign tile__send_data__rdy[1][1+:1] = 1'd0;
	assign tile__send_data__rdy[1][0+:1] = 1'd0;
	assign tile__to_mem_raddr__rdy[1] = 1'd0;
	assign tile__from_mem_rdata__val[1] = 1'd0;
	assign tile__from_mem_rdata__msg[1] = 35'h000000000;
	assign tile__to_mem_waddr__rdy[1] = 1'd0;
	assign tile__to_mem_wdata__rdy[1] = 1'd0;
	assign tile__recv_data__val[2][7+:1] = 1'd0;
	assign tile__recv_data__msg[2][245+:35] = 35'h000000000;
	assign tile__recv_data__val[2][5+:1] = 1'd0;
	assign tile__recv_data__msg[2][175+:35] = 35'h000000000;
	assign tile__recv_data__val[2][3+:1] = 1'd0;
	assign tile__recv_data__msg[2][105+:35] = 35'h000000000;
	assign tile__recv_data__val[2][2+:1] = 1'd0;
	assign tile__recv_data__msg[2][70+:35] = 35'h000000000;
	assign tile__recv_data__val[2][0+:1] = 1'd0;
	assign tile__recv_data__msg[2][0+:35] = 35'h000000000;
	assign tile__send_data__rdy[2][7+:1] = 1'd0;
	assign tile__send_data__rdy[2][5+:1] = 1'd0;
	assign tile__send_data__rdy[2][3+:1] = 1'd0;
	assign tile__send_data__rdy[2][2+:1] = 1'd0;
	assign tile__send_data__rdy[2][0+:1] = 1'd0;
	assign tile__recv_data__val[3][7+:1] = 1'd0;
	assign tile__recv_data__msg[3][245+:35] = 35'h000000000;
	assign tile__recv_data__val[3][4+:1] = 1'd0;
	assign tile__recv_data__msg[3][140+:35] = 35'h000000000;
	assign tile__recv_data__val[3][3+:1] = 1'd0;
	assign tile__recv_data__msg[3][105+:35] = 35'h000000000;
	assign tile__recv_data__val[3][2+:1] = 1'd0;
	assign tile__recv_data__msg[3][70+:35] = 35'h000000000;
	assign tile__recv_data__val[3][1+:1] = 1'd0;
	assign tile__recv_data__msg[3][35+:35] = 35'h000000000;
	assign tile__send_data__rdy[3][7+:1] = 1'd0;
	assign tile__send_data__rdy[3][4+:1] = 1'd0;
	assign tile__send_data__rdy[3][3+:1] = 1'd0;
	assign tile__send_data__rdy[3][2+:1] = 1'd0;
	assign tile__send_data__rdy[3][1+:1] = 1'd0;
	assign tile__to_mem_raddr__rdy[3] = 1'd0;
	assign tile__from_mem_rdata__val[3] = 1'd0;
	assign tile__from_mem_rdata__msg[3] = 35'h000000000;
	assign tile__to_mem_waddr__rdy[3] = 1'd0;
	assign tile__to_mem_wdata__rdy[3] = 1'd0;
endmodule
