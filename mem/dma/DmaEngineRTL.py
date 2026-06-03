"""
==========================================================================
DmaEngineRTL.py
==========================================================================

Simple DMA engine for moving opaque words between an abstract external
memory interface and the CGRA dataSPM.
"""

from pymtl3 import *

from lib.util.common import DMA_MVIN, DMA_MVOUT, CHAR_BIT, StateType, STATE_IDLE, STATE_MVIN_REQ, STATE_MVIN_RESP, STATE_MVIN_WRITE, STATE_MVOUT_READ, STATE_MVOUT_RESP, STATE_MVOUT_WRITE, STATE_MVOUT_WAIT, STATE_DONE


class DmaEngineRTL( Component ):
  """
  The DmaEngineRTL module is responsible for bulk data movement between an
  external DRAM-like memory and the on-chip Scratchpad Memory (dataSPM).

  It supports two main operations:
  - DMA_MVIN:  DRAM -> DMA Engine -> SPM
  - DMA_MVOUT: SPM -> DMA Engine -> DRAM

  Architectural Design:
  - 1 word = 4 bytes = 32 bits in this system.
  - DRAM is byte-addressed which means each unique address points to a byte(8 bits).
  - SPM is word-addressed which means each unique address points to a word(32 bits).
  - The engine uses a 128-bit interface to external memory (4 words per beat)
    and a 32-bit interface to the dataSPM (1 word per cycle).
  - A finite state machine (FSM) manages the command execution flow, including
    requesting memory, waiting for responses, and performing SPM accesses.
  - MVIN logic: Requests 128-bit beats from DRAM, then unpacks them into four
    sequential 32-bit SPM writes.
  - MVOUT logic: Reads four 32-bit words from SPM, packs them into a 128-bit
    beat, and issues a single write request to DRAM.
  """

  def construct( s,
                 spm_data_nbits = 32,  # Bitwidth of a single SPM word
                 mem_data_nbits = 128, # Bitwidth of an external memory beat
                 dram_addr_nbits = 64, # Bitwidth of DRAM addresses
                 spm_addr_nbits = 32,  # Bitwidth of SPM addresses
                 bytes_nbits = 32,     # Bitwidth for transfer size in bytes
                 tag_nbits = 8 ):      # Bitwidth for command tracking tags

    assert mem_data_nbits == spm_data_nbits * 4

    OpcodeType   = mk_bits( 3 )
    DramAddrType = mk_bits( dram_addr_nbits )
    SpmAddrType  = mk_bits( spm_addr_nbits )
    BytesType    = mk_bits( bytes_nbits )
    TagType      = mk_bits( tag_nbits )
    SpmDataType  = mk_bits( spm_data_nbits )
    MemDataType  = mk_bits( mem_data_nbits )
    # Byte mask for SPM write
    SpmMaskType  = mk_bits( spm_data_nbits // CHAR_BIT )
    MemMaskType  = mk_bits( mem_data_nbits // CHAR_BIT )

    # Command interface
    s.dma_cmd_val       = InPort()
    s.dma_cmd_rdy       = OutPort()
    s.dma_cmd_opcode    = InPort( OpcodeType )
    s.dma_cmd_dram_addr = InPort( DramAddrType )
    s.dma_cmd_spm_addr  = InPort( SpmAddrType )
    # An input signal that specifies the number of bytes to transfer.
    s.dma_cmd_bytes     = InPort( BytesType )
    s.dma_cmd_tag       = InPort( TagType )

    s.dma_done_val      = OutPort()
    s.dma_done_rdy      = InPort()
    s.dma_done_tag      = OutPort( TagType )

    # Abstract external memory interface
    # Request to read from DRAM
    s.mem_rd_req_val    = OutPort()
    s.mem_rd_req_rdy    = InPort()
    s.mem_rd_req_addr   = OutPort( DramAddrType )
    # Response from DRAM
    s.mem_rd_resp_val   = InPort()
    s.mem_rd_resp_rdy   = OutPort()
    s.mem_rd_resp_data  = InPort( MemDataType )

    # Request to write to DRAM
    s.mem_wr_req_val    = OutPort()
    s.mem_wr_req_rdy    = InPort()
    s.mem_wr_req_addr   = OutPort( DramAddrType )
    s.mem_wr_req_data   = OutPort( MemDataType )
    s.mem_wr_req_mask   = OutPort( MemMaskType )
    s.mem_wr_resp_val   = InPort()
    s.mem_wr_resp_rdy   = OutPort()

    # SPM interface
    # Request to write to SPM
    s.spm_dma_wval      = OutPort()
    s.spm_dma_wrdy      = InPort()
    s.spm_dma_waddr     = OutPort( SpmAddrType )
    s.spm_dma_wdata     = OutPort( SpmDataType )
    s.spm_dma_wmask     = OutPort( SpmMaskType )

    # Request to read from SPM
    s.spm_dma_rval      = OutPort()
    s.spm_dma_rrdy      = InPort()
    s.spm_dma_raddr     = OutPort( SpmAddrType )

    # Response from SPM
    s.spm_dma_rresp_val  = InPort()
    s.spm_dma_rresp_rdy  = OutPort()
    s.spm_dma_rresp_data = InPort( SpmDataType )

    # State machine definitions

    s.state             = Wire( StateType )
    s.state_next        = Wire( StateType )

    # Combinational logic
    s.opcode_reg        = Wire( OpcodeType )   # Current operation (MVIN/MVOUT)
    s.dram_addr_reg     = Wire( DramAddrType ) # Current DRAM byte address
    s.spm_addr_reg      = Wire( SpmAddrType )  # Current SPM word address
    s.words_left_reg    = Wire( BytesType )    # Number of 32-bit words remaining to transfer
    s.tag_reg           = Wire( TagType )      # Tag of the active command
    s.beat_reg          = Wire( MemDataType )  # Buffer for 128-bit DRAM beat
    s.word_idx_reg      = Wire( Bits2 )        # Index (0-3) of the word within a beat
    s.wr_mask_reg       = Wire( MemMaskType )  # Byte mask for DRAM write

    # Sequential logic
    s.state_ff          = Wire( StateType )
    s.opcode_ff         = Wire( OpcodeType )
    s.dram_addr_ff      = Wire( DramAddrType )
    s.spm_addr_ff       = Wire( SpmAddrType )
    s.words_left_ff     = Wire( BytesType )
    s.tag_ff            = Wire( TagType )
    s.beat_ff           = Wire( MemDataType )
    s.word_idx_ff       = Wire( Bits2 )
    s.wr_mask_ff        = Wire( MemMaskType )

    # Connections
    s.state             //= s.state_ff
    s.opcode_reg        //= s.opcode_ff
    s.dram_addr_reg     //= s.dram_addr_ff
    s.spm_addr_reg      //= s.spm_addr_ff
    s.words_left_reg    //= s.words_left_ff
    s.tag_reg           //= s.tag_ff
    s.beat_reg          //= s.beat_ff
    s.word_idx_reg      //= s.word_idx_ff
    s.wr_mask_reg       //= s.wr_mask_ff

    @update
    def comb_outputs():
      s.dma_cmd_rdy        @= s.state == STATE_IDLE
      s.dma_done_val       @= s.state == STATE_DONE
      s.dma_done_tag       @= s.tag_reg

      s.mem_rd_req_val     @= s.state == STATE_MVIN_REQ
      s.mem_rd_req_addr    @= s.dram_addr_reg
      s.mem_rd_resp_rdy    @= s.state == STATE_MVIN_RESP

      s.mem_wr_req_val     @= s.state == STATE_MVOUT_WRITE
      s.mem_wr_req_addr    @= s.dram_addr_reg
      s.mem_wr_req_data    @= s.beat_reg
      s.mem_wr_req_mask    @= s.wr_mask_reg
      s.mem_wr_resp_rdy    @= s.state == STATE_MVOUT_WAIT

      s.spm_dma_wval       @= s.state == STATE_MVIN_WRITE
      s.spm_dma_waddr      @= s.spm_addr_reg
      s.spm_dma_wmask      @= SpmMaskType( (1 << (spm_data_nbits // CHAR_BIT)) - 1 ) # Write mask for SPM write; always be 0b1111

      if s.word_idx_reg == b2( 0 ): # Writes the first word of the beat to SPM
        s.spm_dma_wdata    @= s.beat_reg[0:spm_data_nbits]
      elif s.word_idx_reg == b2( 1 ): # Writes the second word of the beat to SPM
        s.spm_dma_wdata    @= s.beat_reg[spm_data_nbits:spm_data_nbits*2]
      elif s.word_idx_reg == b2( 2 ): # 3rd word
        s.spm_dma_wdata    @= s.beat_reg[spm_data_nbits*2:spm_data_nbits*3]
      else: # 4th word
        s.spm_dma_wdata    @= s.beat_reg[spm_data_nbits*3:spm_data_nbits*4]

      s.spm_dma_rval       @= s.state == STATE_MVOUT_READ
      s.spm_dma_raddr      @= s.spm_addr_reg
      s.spm_dma_rresp_rdy  @= s.state == STATE_MVOUT_RESP

    @update_ff
    def seq_state():
      if s.reset:
        s.state_ff      <<= STATE_IDLE
        s.opcode_ff     <<= OpcodeType( 0 )
        s.dram_addr_ff  <<= DramAddrType( 0 )
        s.spm_addr_ff   <<= SpmAddrType( 0 )
        s.words_left_ff <<= BytesType( 0 )
        s.tag_ff        <<= TagType( 0 )
        s.beat_ff       <<= MemDataType( 0 )
        s.word_idx_ff   <<= b2( 0 )
        s.wr_mask_ff    <<= MemMaskType( 0 )
      else:
        if s.state == STATE_IDLE:
          if s.dma_cmd_val & s.dma_cmd_rdy: # Receives a new DMA command.
            s.opcode_ff     <<= s.dma_cmd_opcode
            s.dram_addr_ff  <<= s.dma_cmd_dram_addr
            s.spm_addr_ff   <<= s.dma_cmd_spm_addr
            s.words_left_ff <<= s.dma_cmd_bytes >> 2 # Converts the transfer size from bytes to words.
            s.tag_ff        <<= s.dma_cmd_tag
            s.beat_ff       <<= MemDataType( 0 )
            s.word_idx_ff   <<= b2( 0 )
            s.wr_mask_ff    <<= MemMaskType( 0 )

            if s.dma_cmd_bytes == BytesType( 0 ): # No more bytes to transfer.
              s.state_ff    <<= STATE_DONE
            # Still has bytes to transfer.
            elif s.dma_cmd_opcode == OpcodeType( DMA_MVIN ):
              s.state_ff    <<= STATE_MVIN_REQ # Move to the next state: to issue a read request to DRAM.
            else: # DMA_MVOUT
              s.state_ff    <<= STATE_MVOUT_READ # Move to the next state: to issue a read request to SPM.

        elif s.state == STATE_MVIN_REQ: # Issues a read request to DRAM.
          if s.mem_rd_req_val & s.mem_rd_req_rdy:
            s.dram_addr_ff  <<= s.dram_addr_reg + DramAddrType( mem_data_nbits // CHAR_BIT )
            s.state_ff      <<= STATE_MVIN_RESP

        elif s.state == STATE_MVIN_RESP: # Receives a response from DRAM.
          if s.mem_rd_resp_val & s.mem_rd_resp_rdy:
            s.beat_ff       <<= s.mem_rd_resp_data
            s.word_idx_ff   <<= b2( 0 )
            s.state_ff      <<= STATE_MVIN_WRITE # Move to the next state: to write to SPM.

        elif s.state == STATE_MVIN_WRITE: # Writes to SPM.
          if s.spm_dma_wval & s.spm_dma_wrdy:
            # Update the SPM address where write next cycle(+1)
            s.spm_addr_ff   <<= s.spm_addr_reg + SpmAddrType( 1 )
            # Update the number of words remaining to write to SPM.
            s.words_left_ff <<= s.words_left_reg - BytesType( 1 )

            if s.words_left_reg == BytesType( 1 ):
              s.state_ff    <<= STATE_DONE
            elif s.word_idx_reg == b2( 3 ):
              s.word_idx_ff <<= b2( 0 )
              s.state_ff    <<= STATE_MVIN_REQ
            else:
              s.word_idx_ff <<= s.word_idx_reg + b2( 1 )

        elif s.state == STATE_MVOUT_READ:
          if s.spm_dma_rval & s.spm_dma_rrdy:
            s.state_ff      <<= STATE_MVOUT_RESP # Move to the next state: to receive a response from SPM.

        elif s.state == STATE_MVOUT_RESP:
          if s.spm_dma_rresp_val & s.spm_dma_rresp_rdy:
            # Pack the response from SPM into a 128-bit beat by left-shifting.
            if s.word_idx_reg == b2( 0 ): # 1st word
              s.beat_ff <<= concat( s.beat_reg[spm_data_nbits:spm_data_nbits*4],
                                    s.spm_dma_rresp_data )
            elif s.word_idx_reg == b2( 1 ):
              s.beat_ff <<= concat( s.beat_reg[spm_data_nbits*2:spm_data_nbits*4],
                                    s.spm_dma_rresp_data,
                                    s.beat_reg[0:spm_data_nbits] )
            elif s.word_idx_reg == b2( 2 ):
              s.beat_ff <<= concat( s.beat_reg[spm_data_nbits*3:spm_data_nbits*4],
                                    s.spm_dma_rresp_data,
                                    s.beat_reg[0:spm_data_nbits*2] )
            else:
              s.beat_ff <<= concat( s.spm_dma_rresp_data,
                                    s.beat_reg[0:spm_data_nbits*3] )

            s.spm_addr_ff   <<= s.spm_addr_reg + SpmAddrType( 1 )
            s.words_left_ff <<= s.words_left_reg - BytesType( 1 )

            if s.words_left_reg == BytesType( 1 ):
              if s.word_idx_reg == b2( 0 ):
                s.wr_mask_ff <<= MemMaskType( 0x000f )
              elif s.word_idx_reg == b2( 1 ):
                s.wr_mask_ff <<= MemMaskType( 0x00ff )
              elif s.word_idx_reg == b2( 2 ):
                s.wr_mask_ff <<= MemMaskType( 0x0fff )
              else:
                s.wr_mask_ff <<= MemMaskType( 0xffff )
              s.state_ff    <<= STATE_MVOUT_WRITE
            elif s.word_idx_reg == b2( 3 ):
              s.wr_mask_ff  <<= MemMaskType( 0xffff )
              s.state_ff    <<= STATE_MVOUT_WRITE
            else:
              s.word_idx_ff <<= s.word_idx_reg + b2( 1 )
              s.state_ff    <<= STATE_MVOUT_READ

        elif s.state == STATE_MVOUT_WRITE:
          if s.mem_wr_req_val & s.mem_wr_req_rdy:
            s.state_ff    <<= STATE_MVOUT_WAIT

        elif s.state == STATE_MVOUT_WAIT:
          if s.mem_wr_resp_val & s.mem_wr_resp_rdy:
            # Turn to the +16 address after writing 16 bytes data.
            s.dram_addr_ff  <<= s.dram_addr_reg + DramAddrType( mem_data_nbits // CHAR_BIT )
            s.beat_ff       <<= MemDataType( 0 )
            s.word_idx_ff   <<= b2( 0 )
            s.wr_mask_ff    <<= MemMaskType( 0 )

            if s.words_left_reg == BytesType( 0 ):
              s.state_ff    <<= STATE_DONE
            else:
              s.state_ff    <<= STATE_MVOUT_READ

        elif s.state == STATE_DONE:
          if s.dma_done_val & s.dma_done_rdy:
            s.state_ff      <<= STATE_IDLE

  def line_trace( s ):
    return f"dma(state={int(s.state)},tag={int(s.tag_reg)},left={int(s.words_left_reg)})"
