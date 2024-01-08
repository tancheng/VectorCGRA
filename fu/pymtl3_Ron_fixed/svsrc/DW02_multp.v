////////////////////////////////////////////////////////////////////////////////
//
//       This confidential and proprietary software may be used only
//     as authorized by a licensing agreement from Synopsys Inc.
//     In the event of publication, the following notice is applicable:
//
//                    (C) COPYRIGHT 1998  - 2016 SYNOPSYS INC.
//                           ALL RIGHTS RESERVED
//
//       The entire notice above must be reproduced on all authorized
//     copies.
//
// AUTHOR:    Rick Kelly               November 3, 1998
//
// VERSION:   Verilog Simulation Model for DW02_multp
//
// DesignWare_version: 593b2d2a
// DesignWare_release: L-2016.03-DWBB_201603.5.1
//
////////////////////////////////////////////////////////////////////////////////

//-----------------------------------------------------------------------------
//
// ABSTRACT:  Multiplier, parital products
//
//    **** >>>>  NOTE:	This model is architecturally different
//			from the 'wall' implementation of DW02_multp
//			but will generate exactly the same result
//			once the two partial product outputs are
//			added together
//
// MODIFIED:
//
//		RJK  2/22/12  Corrected missed conversion of macro to localparam
//				for non-VCS model (STAR 9000522698)
//
//              Aamir Farooqui 7/11/02
//              Corrected parameter simplied sim model, checking, and X_processing 
//
//------------------------------------------------------------------------------

//ifdef VCS
//include "vcs/DW02_multp.v"
//else

module DW02_multp( a, b, tc, out0, out1 );


// parameters
parameter a_width = 8;
parameter b_width = 8;
parameter out_width = 18;
parameter verif_en = 1;


//-----------------------------------------------------------------------------
// ports
input [a_width-1 : 0]	a;
input [b_width-1 : 0]	b;
input			tc;
output [out_width-1:0]	out0, out1;


//-----------------------------------------------------------------------------
// synopsys translate_off

//-----------------------------------------------------------------------------

  
 
  initial begin : parameter_check
    integer param_err_flg;

    param_err_flg = 0;
    
    
    if (a_width < 1) begin
      param_err_flg = 1;
      $display(
	"ERROR: %m :\n  Invalid value (%d) for parameter a_width (lower bound: 1)",
	a_width );
    end
    
    if (b_width < 1) begin
      param_err_flg = 1;
      $display(
	"ERROR: %m :\n  Invalid value (%d) for parameter b_width (lower bound: 1)",
	b_width );
    end
    
    if (out_width < (a_width+b_width+2)) begin
      param_err_flg = 1;
      $display(
	"ERROR: %m :\n  Invalid value (%d) for parameter out_width (lower bound: (a_width+b_width+2))",
	out_width );
    end
    
    if ( (verif_en < 0) || (verif_en > 3) ) begin
      param_err_flg = 1;
      $display(
	"ERROR: %m :\n  Invalid value (%d) for parameter verif_en (legal range: 0 to 3)",
	verif_en );
    end
  
    if ( param_err_flg == 1) begin
      $display(
        "%m :\n  Simulation aborted due to invalid parameter value(s)");
      $finish;
    end

  end // parameter_check 


   initial begin : verif_en_warning
     $display("The parameter verif_en is set to 0 for this simulator.\nOther values for verif_en are enabled only for VCS.");
   end // verif_en_warning

//-----------------------------------------------------------------------------


localparam npp  = ((a_width/2) + 2);
localparam xdim = (a_width+b_width+1);
localparam bsxt = (a_width+1);

//-----------------------------------------------------------------------------
reg   [xdim-1 : 0]  pp_array [0 : npp-1];
reg   [xdim-1 : 0]	tmp_OUT0, tmp_OUT1;
wire  [a_width+2 : 0]	a_padded;
wire  [xdim-1 : 0]	b_padded;
wire  [xdim-b_width-1 : 0]	temp_padded;
wire  			a_sign, b_sign, out_sign;
wire  [out_width-1:0]   out0_fixed_cs, out1_fixed_cs;
wire  signed [a_width : 0]      a_signed;
wire  signed [b_width : 0]      b_signed;
wire  signed [out_width-1:0] product;
//-----------------------------------------------------------------------------

  assign a_sign = tc & a[a_width-1];
  assign b_sign = tc & b[b_width-1];
  assign a_padded = {a_sign, a_sign, a, 1'b0};
  assign temp_padded = {bsxt{b_sign}};
  assign b_padded = {temp_padded, b};

  always @ (a_padded or b_padded)
  begin : mk_pp_array
    reg [xdim-1 : 0] temp_pp_array [0 : npp-1];
    reg [xdim-1 : 0] next_pp_array [0 : npp-1];
    reg [xdim+3 : 0] temp_pp;
    reg [xdim-1 : 0] new_pp;
    reg [xdim-1 : 0] tmp_pp_carry;
    reg [a_width+2 : 0] temp_a_padded;
    reg [2 : 0] temp_bitgroup;
    integer bit_pair, pp_count, i;

    temp_pp_array[0] = {xdim{1'b0}};

    for (bit_pair=0 ; bit_pair < npp-1 ; bit_pair = bit_pair+1)
    begin
      temp_a_padded = (a_padded >> (bit_pair*2));
      temp_bitgroup = temp_a_padded[2 : 0];

      case (temp_bitgroup)
        3'b000, 3'b111 :
          temp_pp = {xdim{1'b0}};
        3'b001, 3'b010 :
          temp_pp = b_padded;
        3'b011 :
          temp_pp = b_padded << 1;
        3'b100 :
          temp_pp = (~(b_padded << 1) + 1);
        3'b101, 3'b110 :
          temp_pp =  ~b_padded + 1;
        default : temp_pp = {xdim{1'b0}};
      endcase

      temp_pp = temp_pp << (2 * bit_pair);
      new_pp = temp_pp[xdim-1 : 0];
      temp_pp_array[bit_pair+1] = new_pp;
    end
    pp_count = npp;

    while (pp_count > 2)
    begin
      for (i=0 ; i < (pp_count/3) ; i = i+1)
      begin
        next_pp_array[i*2] = temp_pp_array[i*3] ^ temp_pp_array[i*3+1] ^ temp_pp_array[i*3+2];

        tmp_pp_carry = (temp_pp_array[i*3] & temp_pp_array[i*3+1]) |
                       (temp_pp_array[i*3+1] & temp_pp_array[i*3+2]) |
                       (temp_pp_array[i*3] & temp_pp_array[i*3+2]);

        next_pp_array[i*2+1] = tmp_pp_carry << 1;
      end

      if ((pp_count % 3) > 0)
      begin
        for (i=0 ; i < (pp_count % 3) ; i = i + 1)
        next_pp_array[2 * (pp_count/3) + i] = temp_pp_array[3 * (pp_count/3) + i];
      end

      for (i=0 ; i < npp ; i = i + 1) 
        temp_pp_array[i] = next_pp_array[i];

      pp_count = pp_count - (pp_count/3);
    end

    tmp_OUT0 = temp_pp_array[0];

    if (pp_count > 1)
      tmp_OUT1 = temp_pp_array[1];
    else
      tmp_OUT1 = {xdim{1'b0}};
  end // mk_pp_array


  assign out_sign = tmp_OUT0[xdim-1] | tmp_OUT1[xdim-1];
  assign out0 = ((^(a ^ a) !== 1'b0) | (^(b ^ b) !== 1'b0) | (^(tc ^ tc) !== 1'b0)) ? {out_width{1'bx}} 
                : {{out_width-xdim{1'b0}}, tmp_OUT0};
  assign out1 = ((^(a ^ a) !== 1'b0) | (^(b ^ b) !== 1'b0) | (^(tc ^ tc) !== 1'b0)) ? {out_width{1'bx}} 
                : {{out_width-xdim{out_sign}}, tmp_OUT1};

// synopsys translate_on

endmodule
//endif
