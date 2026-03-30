module step_mmio_dma_wrapper
  import step_replay_pkg::*;
(
  input  logic        clk_i,
  input  logic        rst_ni,

  input  logic        mmio_valid_i,
  input  logic        mmio_write_i,
  input  logic [15:0] mmio_addr_i,
  input  logic [31:0] mmio_wdata_i,
  output logic        mmio_ready_o,
  output logic [31:0] mmio_rdata_o,

  output logic        step_done_o,
  output logic [31:0] exit_code_o,

  output logic        dma_mem_valid_o,
  output logic [31:0] dma_mem_addr_o,
  input  logic [31:0] dma_mem_rdata_i,

  output logic [63:0] benchmark_cycle_dbg_o,
  output logic [63:0] first_dma_program_cycle_dbg_o,
  output logic [63:0] first_dma_issue_cycle_dbg_o,
  output logic [63:0] first_dma_stream_cycle_dbg_o,
  output logic [63:0] last_dma_stream_cycle_dbg_o,
  output logic [63:0] first_cgra_metadata_cycle_dbg_o,
  output logic [63:0] last_cgra_metadata_cycle_dbg_o,
  output logic [63:0] first_cgra_bitstream_cycle_dbg_o,
  output logic [63:0] last_cgra_bitstream_cycle_dbg_o,
  output logic [63:0] first_cgra_activity_cycle_dbg_o,
  output logic [63:0] cgra_done_cycle_dbg_o,
  output logic [31:0] dma_transfer_count_dbg_o,
  output logic        dma_transfer_overflow_dbg_o,
  output logic [31:0] dma_transfer_kind_dbg_o [0:255],
  output logic [31:0] dma_transfer_src_dbg_o [0:255],
  output logic [31:0] dma_transfer_len_dbg_o [0:255],
  output logic [63:0] dma_transfer_issue_cycle_dbg_o [0:255],
  output logic [63:0] dma_transfer_start_cycle_dbg_o [0:255],
  output logic [63:0] dma_transfer_end_cycle_dbg_o [0:255],
  output logic [31:0] dma_transfer_words_streamed_dbg_o [0:255],

  output logic [43:0] step_ld_mem_addr_o [0:1],
  input  logic [31:0] step_ld_mem_rdata_i [0:1],
  output logic        step_st_mem_we_o [0:1],
  output logic [43:0] step_st_mem_addr_o [0:1],
  output logic [31:0] step_st_mem_wdata_o [0:1],
  output logic [3:0]  step_st_mem_be_o [0:1]
);

  localparam int unsigned META_WORDS = STEP_META_WORDS;
  localparam int unsigned BIT_WORDS  = STEP_BIT_WORDS;
  localparam int unsigned BIT_STORE_DEPTH = 256;
  localparam int unsigned PC_REQ_BITS = 5;
  localparam int unsigned PC_TRIGGER_COUNT_BITS = 5;
  localparam int unsigned TRIGGER_KEY_BITS = PC_REQ_BITS + PC_TRIGGER_COUNT_BITS;
  localparam int unsigned TRIGGER_KEY_COUNT = (1 << TRIGGER_KEY_BITS);
  localparam int unsigned PENDING_TRIGGER_DEPTH = 4096;
  localparam int unsigned DMA_BENCH_MAX_TRANSFERS = 256;

  logic [31:0] meta_words_q [0:META_WORDS-1];
  logic [31:0] bit_words_q  [0:BIT_WORDS-1];
  logic [$clog2(META_WORDS+1)-1:0] meta_word_count_q;
  logic [$clog2(BIT_WORDS+1)-1:0]  bit_word_count_q;

  logic [META_WORDS*32-1:0] meta_bits_ext;
  logic [BIT_WORDS*32-1:0]  bit_bits_ext;
  logic [STEP_META_BITS-1:0] meta_bits;
  logic [STEP_BIT_BITS-1:0]  bit_bits;
  logic [BIT_WORDS*32-1:0]  bit_active_bits_ext;
  logic [STEP_BIT_BITS-1:0] bit_active_bits;

  CfgMetadataPkt_16_8__a661a3cccaed7097 metadata_msg;
  TileBitstreamPkt_3_1__dcf8fa7971bb4bbc bitstream_msg;
  TileBitstreamPkt_3_1__dcf8fa7971bb4bbc bitstream_active_msg;

  logic metadata_pending_q;
  logic bitstream_pending_q;
  logic [BIT_WORDS*32-1:0] bit_packet_store_q [0:BIT_STORE_DEPTH-1];
  logic trigger_map_valid_q [0:TRIGGER_KEY_COUNT-1];
  integer trigger_map_start_q [0:TRIGGER_KEY_COUNT-1];
  logic [PC_REQ_BITS-1:0] pending_trigger_pc_q [0:PENDING_TRIGGER_DEPTH-1];
  logic [PC_TRIGGER_COUNT_BITS-1:0] pending_trigger_group_count_q [0:PENDING_TRIGGER_DEPTH-1];
  integer pending_trigger_wr_ptr_q;
  integer pending_trigger_rd_ptr_q;
  integer pending_trigger_level_q;
  integer bit_store_wr_ptr_q;
  integer bit_next_unassigned_start_q;
  integer bit_active_start_q;
  integer bit_active_count_q;
  integer bit_active_idx_q;
  logic   bit_active_valid_q;

  logic [31:0] dma_src_q;
  logic [31:0] dma_dst_q;
  logic [31:0] dma_len_q;
  logic [31:0] dma_cmd_q;
  logic [31:0] exit_code_q;
  logic        dma_busy_q;
  logic [31:0] dma_idx_q;
  logic [31:0] dma_active_transfer_q;
  integer      debug_mmio_count_q;
  integer      debug_step_event_count_q;
  integer      debug_step_mem_count_q;
  integer      debug_mmio_read_count_q;
  integer      debug_done_status_read_count_q;
  logic        debug_exit_write_seen_q;

  logic done_seen_q;
  logic error_q;
  logic send_to_cpu_done_q;
  logic [63:0] benchmark_cycle_q;
  logic [63:0] cycle_now;
  logic [63:0] first_dma_program_cycle_q;
  logic [63:0] first_dma_issue_cycle_q;
  logic [63:0] first_dma_stream_cycle_q;
  logic [63:0] last_dma_stream_cycle_q;
  logic [63:0] first_cgra_metadata_cycle_q;
  logic [63:0] last_cgra_metadata_cycle_q;
  logic [63:0] first_cgra_bitstream_cycle_q;
  logic [63:0] last_cgra_bitstream_cycle_q;
  logic [63:0] first_cgra_activity_cycle_q;
  logic [63:0] cgra_done_cycle_q;
  logic [31:0] dma_transfer_count_q;
  logic        dma_transfer_overflow_q;
  logic [31:0] dma_transfer_kind_q [0:DMA_BENCH_MAX_TRANSFERS-1];
  logic [31:0] dma_transfer_src_q [0:DMA_BENCH_MAX_TRANSFERS-1];
  logic [31:0] dma_transfer_len_q [0:DMA_BENCH_MAX_TRANSFERS-1];
  logic [63:0] dma_transfer_issue_cycle_q [0:DMA_BENCH_MAX_TRANSFERS-1];
  logic [63:0] dma_transfer_start_cycle_q [0:DMA_BENCH_MAX_TRANSFERS-1];
  logic [63:0] dma_transfer_end_cycle_q [0:DMA_BENCH_MAX_TRANSFERS-1];
  logic [31:0] dma_transfer_words_streamed_q [0:DMA_BENCH_MAX_TRANSFERS-1];

  logic send_to_cpu_done;
  logic [4:0] pc_req;
  logic [0:0] pc_req_trigger;
  logic [4:0] pc_req_trigger_count;
  logic [0:0] pc_req_trigger_complete_q;
  logic recv_from_cpu_metadata_pkt__rdy;
  logic recv_from_cpu_bitstream_pkt__rdy;

  logic [43:0] ld_axi__addr [0:1];
  logic [0:0]  ld_axi__addr_rdy [0:1];
  logic [0:0]  ld_axi__addr_val [0:1];
  logic [1:0]  ld_axi__burst [0:1];
  logic [3:0]  ld_axi__cache [0:1];
  logic [31:0] ld_axi__data [0:1];
  logic [0:0]  ld_axi__data_ready [0:1];
  logic [0:0]  ld_axi__data_valid [0:1];
  logic [8:0]  ld_axi__id [0:1];
  logic [7:0]  ld_axi__len [0:1];
  logic [1:0]  ld_axi__resp [0:1];
  logic [8:0]  ld_axi__resp_id [0:1];
  logic [0:0]  ld_axi__resp_last [0:1];
  logic [2:0]  ld_axi__size [0:1];

  logic [43:0] st_axi__addr [0:1];
  logic [0:0]  st_axi__addr_rdy [0:1];
  logic [0:0]  st_axi__addr_val [0:1];
  logic [1:0]  st_axi__burst [0:1];
  logic [3:0]  st_axi__cache [0:1];
  logic [31:0] st_axi__data [0:1];
  logic [0:0]  st_axi__data_ready [0:1];
  logic [0:0]  st_axi__data_valid [0:1];
  logic [8:0]  st_axi__id [0:1];
  logic [7:0]  st_axi__len [0:1];
  logic [1:0]  st_axi__resp [0:1];
  logic [8:0]  st_axi__resp_id [0:1];
  logic [0:0]  st_axi__resp_last [0:1];
  logic [0:0]  st_axi__resp_ready [0:1];
  logic [0:0]  st_axi__resp_valid [0:1];
  logic [2:0]  st_axi__size [0:1];
  logic [15:0] st_axi__str_bytes [0:1];

  logic [31:0] ld_data_pipe_q [0:1];
  logic [8:0]  ld_id_pipe_q   [0:1];
  logic        ld_valid_pipe_q[0:1];

  logic [43:0] st_addr_pipe_q [0:1];
  logic [8:0]  st_resp_id_q   [0:1];
  logic        st_resp_pending_q [0:1];
  integer      ld_case_idx_q [0:1];

  integer i;

  assign cycle_now = benchmark_cycle_q + 64'd1;
  assign benchmark_cycle_dbg_o = benchmark_cycle_q;
  assign first_dma_program_cycle_dbg_o = first_dma_program_cycle_q;
  assign first_dma_issue_cycle_dbg_o = first_dma_issue_cycle_q;
  assign first_dma_stream_cycle_dbg_o = first_dma_stream_cycle_q;
  assign last_dma_stream_cycle_dbg_o = last_dma_stream_cycle_q;
  assign first_cgra_metadata_cycle_dbg_o = first_cgra_metadata_cycle_q;
  assign last_cgra_metadata_cycle_dbg_o = last_cgra_metadata_cycle_q;
  assign first_cgra_bitstream_cycle_dbg_o = first_cgra_bitstream_cycle_q;
  assign last_cgra_bitstream_cycle_dbg_o = last_cgra_bitstream_cycle_q;
  assign first_cgra_activity_cycle_dbg_o = first_cgra_activity_cycle_q;
  assign cgra_done_cycle_dbg_o = cgra_done_cycle_q;
  assign dma_transfer_count_dbg_o = dma_transfer_count_q;
  assign dma_transfer_overflow_dbg_o = dma_transfer_overflow_q;

  generate
    for (genvar dbg_idx = 0; dbg_idx < DMA_BENCH_MAX_TRANSFERS; dbg_idx++) begin : gen_dma_bench_dbg
      assign dma_transfer_kind_dbg_o[dbg_idx] = dma_transfer_kind_q[dbg_idx];
      assign dma_transfer_src_dbg_o[dbg_idx] = dma_transfer_src_q[dbg_idx];
      assign dma_transfer_len_dbg_o[dbg_idx] = dma_transfer_len_q[dbg_idx];
      assign dma_transfer_issue_cycle_dbg_o[dbg_idx] = dma_transfer_issue_cycle_q[dbg_idx];
      assign dma_transfer_start_cycle_dbg_o[dbg_idx] = dma_transfer_start_cycle_q[dbg_idx];
      assign dma_transfer_end_cycle_dbg_o[dbg_idx] = dma_transfer_end_cycle_q[dbg_idx];
      assign dma_transfer_words_streamed_dbg_o[dbg_idx] = dma_transfer_words_streamed_q[dbg_idx];
    end
  endgenerate

`include "step_accel_case_model.svh"

  always_comb begin
    meta_bits_ext = '0;
    for (int idx = 0; idx < META_WORDS; idx++) begin
      meta_bits_ext[idx*32 +: 32] = meta_words_q[idx];
    end
    meta_bits = meta_bits_ext[STEP_META_BITS-1:0];
  end

  always_comb begin
    bit_bits_ext = '0;
    for (int idx = 0; idx < BIT_WORDS; idx++) begin
      bit_bits_ext[idx*32 +: 32] = bit_words_q[idx];
    end
    bit_bits = bit_bits_ext[STEP_BIT_BITS-1:0];
  end

  always_comb begin
    bit_active_bits_ext = '0;
    if (bit_active_valid_q &&
        (bit_active_idx_q < bit_active_count_q) &&
        ((bit_active_start_q + bit_active_idx_q) < bit_store_wr_ptr_q)) begin
      bit_active_bits_ext = bit_packet_store_q[bit_active_start_q + bit_active_idx_q];
    end
    bit_active_bits = bit_active_bits_ext[STEP_BIT_BITS-1:0];
  end

  assign metadata_msg  = CfgMetadataPkt_16_8__a661a3cccaed7097'(meta_bits);
  assign bitstream_msg = TileBitstreamPkt_3_1__dcf8fa7971bb4bbc'(bit_bits);
  assign bitstream_active_msg = TileBitstreamPkt_3_1__dcf8fa7971bb4bbc'(bit_active_bits);

  assign mmio_ready_o = 1'b1;
  assign step_done_o  = done_seen_q;
  assign exit_code_o  = exit_code_q;
  assign dma_mem_valid_o = dma_busy_q;
  assign dma_mem_addr_o  = dma_src_q + (dma_idx_q << 2);

  always_comb begin
    unique case (mmio_addr_i)
      STEP_MMIO_STATUS_ADDR: begin
        mmio_rdata_o = {28'd0, dma_busy_q, error_q, metadata_pending_q | bitstream_pending_q, done_seen_q};
      end
      STEP_MMIO_DMA_SRC_ADDR: mmio_rdata_o = dma_src_q;
      STEP_MMIO_DMA_DST_ADDR: mmio_rdata_o = dma_dst_q;
      STEP_MMIO_DMA_LEN_ADDR: mmio_rdata_o = dma_len_q;
      STEP_MMIO_DMA_CMD_ADDR: mmio_rdata_o = dma_cmd_q;
      STEP_MMIO_EXIT_ADDR: mmio_rdata_o = exit_code_q;
      default: mmio_rdata_o = 32'd0;
    endcase
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      meta_word_count_q  <= '0;
      bit_word_count_q   <= '0;
      metadata_pending_q <= 1'b0;
      bitstream_pending_q<= 1'b0;
      pending_trigger_wr_ptr_q <= 0;
      pending_trigger_rd_ptr_q <= 0;
      pending_trigger_level_q <= 0;
      bit_store_wr_ptr_q <= 0;
      bit_next_unassigned_start_q <= 0;
      bit_active_start_q <= 0;
      bit_active_count_q <= 0;
      bit_active_idx_q <= 0;
      bit_active_valid_q <= 1'b0;
      dma_src_q          <= '0;
      dma_dst_q          <= '0;
      dma_len_q          <= '0;
      dma_cmd_q          <= '0;
      dma_busy_q         <= 1'b0;
      dma_idx_q          <= '0;
      dma_active_transfer_q <= '0;
      exit_code_q        <= '0;
      done_seen_q        <= 1'b0;
      error_q            <= 1'b0;
      send_to_cpu_done_q <= 1'b0;
      benchmark_cycle_q  <= '0;
      first_dma_program_cycle_q <= '0;
      first_dma_issue_cycle_q <= '0;
      first_dma_stream_cycle_q <= '0;
      last_dma_stream_cycle_q <= '0;
      first_cgra_metadata_cycle_q <= '0;
      last_cgra_metadata_cycle_q <= '0;
      first_cgra_bitstream_cycle_q <= '0;
      last_cgra_bitstream_cycle_q <= '0;
      first_cgra_activity_cycle_q <= '0;
      cgra_done_cycle_q  <= '0;
      dma_transfer_count_q <= '0;
      dma_transfer_overflow_q <= 1'b0;
      pc_req_trigger_complete_q <= 1'b0;
      debug_mmio_count_q <= 0;
      debug_step_event_count_q <= 0;
      debug_step_mem_count_q <= 0;
      debug_mmio_read_count_q <= 0;
      debug_done_status_read_count_q <= 0;
      debug_exit_write_seen_q <= 1'b0;
      for (i = 0; i < META_WORDS; i++) meta_words_q[i] <= '0;
      for (i = 0; i < BIT_WORDS; i++)  bit_words_q[i]  <= '0;
      for (i = 0; i < TRIGGER_KEY_COUNT; i++) begin
        trigger_map_valid_q[i] <= 1'b0;
        trigger_map_start_q[i] <= 0;
      end
      for (i = 0; i < DMA_BENCH_MAX_TRANSFERS; i++) begin
        dma_transfer_kind_q[i] <= '0;
        dma_transfer_src_q[i] <= '0;
        dma_transfer_len_q[i] <= '0;
        dma_transfer_issue_cycle_q[i] <= '0;
        dma_transfer_start_cycle_q[i] <= '0;
        dma_transfer_end_cycle_q[i] <= '0;
        dma_transfer_words_streamed_q[i] <= '0;
      end
    end else begin
      benchmark_cycle_q <= cycle_now;
      send_to_cpu_done_q <= send_to_cpu_done;
      pc_req_trigger_complete_q <= 1'b0;

      if (mmio_valid_i && mmio_write_i) begin
        if (debug_mmio_count_q < 32) begin
          $display("[step_mmio] write addr=%04x data=%08x", mmio_addr_i, mmio_wdata_i);
          debug_mmio_count_q <= debug_mmio_count_q + 1;
        end
        unique case (mmio_addr_i)
          STEP_MMIO_CTRL_ADDR: begin
            if (mmio_wdata_i[0]) done_seen_q <= 1'b0;
            if (mmio_wdata_i[1]) error_q <= 1'b0;
          end
          STEP_MMIO_META_DATA_ADDR: begin
            if (meta_word_count_q < META_WORDS) begin
              meta_words_q[meta_word_count_q] <= mmio_wdata_i;
              meta_word_count_q <= meta_word_count_q + 1'b1;
            end else begin
              error_q <= 1'b1;
            end
          end
          STEP_MMIO_META_COMMIT_ADDR: begin
            metadata_pending_q <= 1'b1;
            meta_word_count_q <= '0;
          end
          STEP_MMIO_BIT_DATA_ADDR: begin
            if (bit_word_count_q < BIT_WORDS) begin
              bit_words_q[bit_word_count_q] <= mmio_wdata_i;
              bit_word_count_q <= bit_word_count_q + 1'b1;
            end else begin
              error_q <= 1'b1;
            end
          end
          STEP_MMIO_BIT_COMMIT_ADDR: begin
            bitstream_pending_q <= 1'b1;
            bit_word_count_q <= '0;
          end
          STEP_MMIO_DMA_SRC_ADDR: begin
            dma_src_q <= mmio_wdata_i;
            if (first_dma_program_cycle_q == 64'd0) first_dma_program_cycle_q <= cycle_now;
          end
          STEP_MMIO_DMA_DST_ADDR: begin
            dma_dst_q <= mmio_wdata_i;
            if (first_dma_program_cycle_q == 64'd0) first_dma_program_cycle_q <= cycle_now;
          end
          STEP_MMIO_DMA_LEN_ADDR: begin
            dma_len_q <= mmio_wdata_i;
            if (first_dma_program_cycle_q == 64'd0) first_dma_program_cycle_q <= cycle_now;
          end
          STEP_MMIO_DMA_CMD_ADDR: begin
            dma_cmd_q <= mmio_wdata_i;
            if (first_dma_program_cycle_q == 64'd0) first_dma_program_cycle_q <= cycle_now;
            if ((mmio_wdata_i == STEP_DMA_CMD_META) || (mmio_wdata_i == STEP_DMA_CMD_BIT)) begin
              dma_busy_q <= 1'b1;
              dma_idx_q <= '0;
              dma_active_transfer_q <= dma_transfer_count_q;
              if (first_dma_issue_cycle_q == 64'd0) first_dma_issue_cycle_q <= cycle_now;
              if (dma_transfer_count_q < DMA_BENCH_MAX_TRANSFERS) begin
                dma_transfer_kind_q[dma_transfer_count_q] <= mmio_wdata_i;
                dma_transfer_src_q[dma_transfer_count_q] <= dma_src_q;
                dma_transfer_len_q[dma_transfer_count_q] <= dma_len_q;
                dma_transfer_issue_cycle_q[dma_transfer_count_q] <= cycle_now;
                dma_transfer_start_cycle_q[dma_transfer_count_q] <= '0;
                dma_transfer_end_cycle_q[dma_transfer_count_q] <= '0;
                dma_transfer_words_streamed_q[dma_transfer_count_q] <= '0;
                dma_transfer_count_q <= dma_transfer_count_q + 1'b1;
              end else begin
                dma_transfer_overflow_q <= 1'b1;
              end
            end
          end
          STEP_MMIO_EXIT_ADDR: begin
            exit_code_q <= mmio_wdata_i;
            if (!debug_exit_write_seen_q) begin
              $display("[step_mmio] exit write data=%08x done=%0d", mmio_wdata_i, done_seen_q);
              debug_exit_write_seen_q <= 1'b1;
            end
          end
          default: begin end
        endcase
      end

      if (mmio_valid_i && ~mmio_write_i && (debug_mmio_read_count_q < 16)) begin
        if (mmio_addr_i == STEP_MMIO_STATUS_ADDR) begin
          $display("[step_mmio] read status data=%08x done=%0d busy=%0d err=%0d pending=%0d",
                   mmio_rdata_o, done_seen_q, dma_busy_q, error_q, metadata_pending_q | bitstream_pending_q);
          debug_mmio_read_count_q <= debug_mmio_read_count_q + 1;
        end else if (mmio_addr_i == STEP_MMIO_EXIT_ADDR) begin
          $display("[step_mmio] read exit data=%08x", mmio_rdata_o);
          debug_mmio_read_count_q <= debug_mmio_read_count_q + 1;
        end
      end

      if (mmio_valid_i && ~mmio_write_i && done_seen_q &&
          (mmio_addr_i == STEP_MMIO_STATUS_ADDR) &&
          (debug_done_status_read_count_q < 16)) begin
        $display("[step_mmio] post_done status read data=%08x done=%0d busy=%0d err=%0d pending=%0d",
                 mmio_rdata_o, done_seen_q, dma_busy_q, error_q, metadata_pending_q | bitstream_pending_q);
        debug_done_status_read_count_q <= debug_done_status_read_count_q + 1;
      end

      if (dma_busy_q) begin
        if (dma_idx_q < dma_len_q) begin
          if (first_dma_stream_cycle_q == 64'd0) first_dma_stream_cycle_q <= cycle_now;
          last_dma_stream_cycle_q <= cycle_now;
          if (dma_active_transfer_q < DMA_BENCH_MAX_TRANSFERS) begin
            if (dma_transfer_words_streamed_q[dma_active_transfer_q] == 32'd0) begin
              dma_transfer_start_cycle_q[dma_active_transfer_q] <= cycle_now;
            end
            dma_transfer_end_cycle_q[dma_active_transfer_q] <= cycle_now;
            dma_transfer_words_streamed_q[dma_active_transfer_q] <=
              dma_transfer_words_streamed_q[dma_active_transfer_q] + 1'b1;
          end
          if (dma_cmd_q == STEP_DMA_CMD_META) begin
            if (dma_idx_q < META_WORDS) begin
              meta_words_q[dma_idx_q[$clog2(META_WORDS+1)-1:0]] <= dma_mem_rdata_i;
            end
          end else if (dma_cmd_q == STEP_DMA_CMD_BIT) begin
            if (dma_idx_q < BIT_WORDS) begin
              bit_words_q[dma_idx_q[$clog2(BIT_WORDS+1)-1:0]] <= dma_mem_rdata_i;
            end
          end
          dma_idx_q <= dma_idx_q + 1'b1;
        end else begin
          dma_busy_q <= 1'b0;
          if (dma_cmd_q == STEP_DMA_CMD_META) begin
            metadata_pending_q <= 1'b1;
        end else if (dma_cmd_q == STEP_DMA_CMD_BIT) begin
            if (bit_store_wr_ptr_q < BIT_STORE_DEPTH) begin
              bit_packet_store_q[bit_store_wr_ptr_q] <= bit_bits_ext;
              bit_store_wr_ptr_q <= bit_store_wr_ptr_q + 1;
            end else begin
              error_q <= 1'b1;
            end
          end
          dma_cmd_q <= STEP_DMA_CMD_NONE;
        end
      end

      if (send_to_cpu_done & ~send_to_cpu_done_q) begin
        $display("[step_mmio] accelerator done");
        done_seen_q <= 1'b1;
        if (cgra_done_cycle_q == 64'd0) cgra_done_cycle_q <= cycle_now;
      end

      if (pc_req_trigger && (debug_step_event_count_q < 16)) begin
        $display("[step_mmio] pc_req_trigger pc=%0d tiles=%0d", pc_req, pc_req_trigger_count);
        debug_step_event_count_q <= debug_step_event_count_q + 1;
      end

      if (pc_req_trigger) begin
        if (pending_trigger_level_q < PENDING_TRIGGER_DEPTH) begin
          pending_trigger_pc_q[pending_trigger_wr_ptr_q] <= pc_req;
          pending_trigger_group_count_q[pending_trigger_wr_ptr_q] <= pc_req_trigger_count;
          if (pending_trigger_wr_ptr_q == (PENDING_TRIGGER_DEPTH - 1)) begin
            pending_trigger_wr_ptr_q <= 0;
          end else begin
            pending_trigger_wr_ptr_q <= pending_trigger_wr_ptr_q + 1;
          end
          pending_trigger_level_q <= pending_trigger_level_q + 1;
        end else begin
          error_q <= 1'b1;
        end
      end

      if (metadata_pending_q && recv_from_cpu_metadata_pkt__rdy) begin
        if (first_cgra_metadata_cycle_q == 64'd0) first_cgra_metadata_cycle_q <= cycle_now;
        last_cgra_metadata_cycle_q <= cycle_now;
        metadata_pending_q <= 1'b0;
      end
      if (bit_active_valid_q && recv_from_cpu_bitstream_pkt__rdy) begin
        if (first_cgra_bitstream_cycle_q == 64'd0) first_cgra_bitstream_cycle_q <= cycle_now;
        last_cgra_bitstream_cycle_q <= cycle_now;
        if ((bit_active_idx_q + 1) >= bit_active_count_q) begin
          bit_active_valid_q <= 1'b0;
          bit_active_count_q <= 0;
          bit_active_idx_q <= 0;
          pc_req_trigger_complete_q <= 1'b1;
        end else begin
          bit_active_idx_q <= bit_active_idx_q + 1;
        end
      end

      if (((!bit_active_valid_q) ||
           (bit_active_valid_q && recv_from_cpu_bitstream_pkt__rdy &&
            ((bit_active_idx_q + 1) >= bit_active_count_q))) &&
          (pending_trigger_level_q > 0)) begin
        int unsigned pending_pc;
        int unsigned requested_count;
        int unsigned trigger_key;
        int unsigned trigger_start;
        logic trigger_start_valid;
        logic trigger_ready;

        pending_pc = pending_trigger_pc_q[pending_trigger_rd_ptr_q];
        requested_count = pending_trigger_group_count_q[pending_trigger_rd_ptr_q];
        trigger_key = (pending_pc << PC_TRIGGER_COUNT_BITS) | requested_count;
        trigger_start_valid = 1'b1;
        trigger_ready = 1'b1;

        if (trigger_map_valid_q[trigger_key]) begin
          trigger_start = trigger_map_start_q[trigger_key];
          if ((trigger_start + requested_count) > bit_store_wr_ptr_q) begin
            trigger_ready = 1'b0;
          end
        end else begin
          trigger_start = bit_next_unassigned_start_q;
          if ((trigger_start + requested_count) > bit_store_wr_ptr_q) begin
            trigger_ready = 1'b0;
          end else begin
            trigger_map_valid_q[trigger_key] <= 1'b1;
            trigger_map_start_q[trigger_key] <= trigger_start;
            bit_next_unassigned_start_q <= trigger_start + requested_count;
          end
        end

        if (trigger_ready) begin
          if (pending_trigger_rd_ptr_q == (PENDING_TRIGGER_DEPTH - 1)) begin
            pending_trigger_rd_ptr_q <= 0;
          end else begin
            pending_trigger_rd_ptr_q <= pending_trigger_rd_ptr_q + 1;
          end
          pending_trigger_level_q <= pending_trigger_level_q - 1;

          if (requested_count == 0) begin
            pc_req_trigger_complete_q <= 1'b1;
          end else if (trigger_start_valid) begin
            bit_active_start_q <= trigger_start;
            bit_active_count_q <= requested_count;
            bit_active_idx_q <= 0;
            bit_active_valid_q <= 1'b1;
          end
        end
      end
    end
  end

  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      for (i = 0; i < 2; i++) begin
        ld_valid_pipe_q[i] <= 1'b0;
        ld_data_pipe_q[i]  <= '0;
        ld_id_pipe_q[i]    <= '0;
        st_addr_pipe_q[i]  <= '0;
        st_resp_id_q[i]    <= '0;
        st_resp_pending_q[i] <= 1'b0;
        ld_case_idx_q[i]   <= 0;
      end
    end else begin
      for (i = 0; i < 2; i++) begin
        ld_valid_pipe_q[i] <= ld_axi__addr_val[i] & ld_axi__addr_rdy[i];
        if (i == 0) begin
          if (ld_case_idx_q[i] < STEP_CASE_LD_COUNT_0) begin
            ld_data_pipe_q[i] <= step_case_ld_data_0[ld_case_idx_q[i]];
            if (ld_axi__addr_val[i] & ld_axi__addr_rdy[i]) begin
              ld_case_idx_q[i] <= ld_case_idx_q[i] + 1;
            end
          end else begin
            ld_data_pipe_q[i] <= step_ld_mem_rdata_i[i];
          end
        end else begin
          if (ld_case_idx_q[i] < STEP_CASE_LD_COUNT_1) begin
            ld_data_pipe_q[i] <= step_case_ld_data_1[ld_case_idx_q[i]];
            if (ld_axi__addr_val[i] & ld_axi__addr_rdy[i]) begin
              ld_case_idx_q[i] <= ld_case_idx_q[i] + 1;
            end
          end else begin
            ld_data_pipe_q[i] <= step_ld_mem_rdata_i[i];
          end
        end
        ld_id_pipe_q[i]    <= ld_axi__id[i];

        if (st_axi__addr_val[i] & st_axi__addr_rdy[i]) begin
          st_addr_pipe_q[i] <= st_axi__addr[i];
          st_resp_id_q[i] <= st_axi__id[i];
          st_resp_pending_q[i] <= 1'b1;
        end else if (st_axi__resp_valid[i] & st_axi__resp_ready[i]) begin
          st_resp_pending_q[i] <= 1'b0;
        end
      end
    end
  end

  generate
    for (genvar p = 0; p < 2; p++) begin : gen_axi_models
      assign step_ld_mem_addr_o[p] = ld_axi__addr[p];

      assign step_st_mem_we_o[p]   = st_axi__data_valid[p] & st_axi__data_ready[p];
      assign step_st_mem_addr_o[p] = st_addr_pipe_q[p];
      assign step_st_mem_wdata_o[p]= st_axi__data[p];
      assign step_st_mem_be_o[p]   = st_axi__str_bytes[p][3:0];

      assign ld_axi__addr_rdy[p]   = 1'b1;
      assign ld_axi__data[p]       = ld_data_pipe_q[p];
      assign ld_axi__data_valid[p] = ld_valid_pipe_q[p];
      assign ld_axi__resp[p]       = 2'b00;
      assign ld_axi__resp_id[p]    = ld_id_pipe_q[p];
      assign ld_axi__resp_last[p]  = 1'b0;

      assign st_axi__addr_rdy[p]   = 1'b1;
      assign st_axi__data_ready[p] = 1'b1;
      assign st_axi__resp[p]       = 2'b00;
      assign st_axi__resp_id[p]    = st_resp_id_q[p];
      assign st_axi__resp_last[p]  = 1'b0;
      assign st_axi__resp_valid[p] = st_resp_pending_q[p];
    end
  endgenerate

  always_ff @(posedge clk_i) begin
    if (rst_ni) begin
      for (int p = 0; p < 2; p++) begin
        if ((ld_axi__addr_val[p] & ld_axi__addr_rdy[p]) && (debug_step_mem_count_q < 16)) begin
          $display("[step_mmio] step ld port=%0d addr=%08x", p, ld_axi__addr[p][31:0]);
          debug_step_mem_count_q <= debug_step_mem_count_q + 1;
        end
        if ((ld_axi__addr_val[p] & ld_axi__addr_rdy[p]) && (first_cgra_activity_cycle_q == 64'd0)) begin
          first_cgra_activity_cycle_q <= cycle_now;
        end
        if ((step_st_mem_we_o[p]) && (debug_step_mem_count_q < 16)) begin
          $display("[step_mmio] step st port=%0d addr=%08x data=%08x be=%x", p, step_st_mem_addr_o[p][31:0], step_st_mem_wdata_o[p], step_st_mem_be_o[p]);
          debug_step_mem_count_q <= debug_step_mem_count_q + 1;
        end
        if (step_st_mem_we_o[p] && (first_cgra_activity_cycle_q == 64'd0)) begin
          first_cgra_activity_cycle_q <= cycle_now;
        end
      end
    end
  end

  STEP_CgraRTL__2c9482af1bbb680a i_step (
    .clk(clk_i),
    .reset(~rst_ni),
    .cfg_load_sel(),
    .pc_req(pc_req),
    .pc_req_trigger(pc_req_trigger),
    .pc_req_trigger_complete(pc_req_trigger_complete_q),
    .pc_req_trigger_count(pc_req_trigger_count),
    .send_to_cpu_done(send_to_cpu_done),
    .ld_axi__addr(ld_axi__addr),
    .ld_axi__addr_rdy(ld_axi__addr_rdy),
    .ld_axi__addr_val(ld_axi__addr_val),
    .ld_axi__burst(ld_axi__burst),
    .ld_axi__cache(ld_axi__cache),
    .ld_axi__data(ld_axi__data),
    .ld_axi__data_ready(ld_axi__data_ready),
    .ld_axi__data_valid(ld_axi__data_valid),
    .ld_axi__id(ld_axi__id),
    .ld_axi__len(ld_axi__len),
    .ld_axi__resp(ld_axi__resp),
    .ld_axi__resp_id(ld_axi__resp_id),
    .ld_axi__resp_last(ld_axi__resp_last),
    .ld_axi__size(ld_axi__size),
    .recv_from_cpu_bitstream_pkt__msg(bitstream_active_msg),
    .recv_from_cpu_bitstream_pkt__rdy(recv_from_cpu_bitstream_pkt__rdy),
    .recv_from_cpu_bitstream_pkt__val(bit_active_valid_q),
    .recv_from_cpu_metadata_pkt__msg(metadata_msg),
    .recv_from_cpu_metadata_pkt__rdy(recv_from_cpu_metadata_pkt__rdy),
    .recv_from_cpu_metadata_pkt__val(metadata_pending_q),
    .st_axi__addr(st_axi__addr),
    .st_axi__addr_rdy(st_axi__addr_rdy),
    .st_axi__addr_val(st_axi__addr_val),
    .st_axi__burst(st_axi__burst),
    .st_axi__cache(st_axi__cache),
    .st_axi__data(st_axi__data),
    .st_axi__data_ready(st_axi__data_ready),
    .st_axi__data_valid(st_axi__data_valid),
    .st_axi__id(st_axi__id),
    .st_axi__len(st_axi__len),
    .st_axi__resp(st_axi__resp),
    .st_axi__resp_id(st_axi__resp_id),
    .st_axi__resp_last(st_axi__resp_last),
    .st_axi__resp_ready(st_axi__resp_ready),
    .st_axi__resp_valid(st_axi__resp_valid),
    .st_axi__size(st_axi__size),
    .st_axi__str_bytes(st_axi__str_bytes)
  );

endmodule
