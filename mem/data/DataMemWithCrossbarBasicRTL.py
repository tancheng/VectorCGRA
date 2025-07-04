"""
==========================================================================
DataMemWithCrossbarBasicRTL.py
==========================================================================
Only contains write xbar and store related operations, as blocking and 
non-blocking have different read xbar and load related operations

Author : Yufei Yang
  Date : July 3, 2025
"""

from pymtl3.stdlib.primitive import RegisterFile
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.basic.val_rdy.queues import BypassQueueRTL
from ...lib.messages import *
from ...noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL


class DataMemWithCrossbarBasicRTL(Component):

  def construct(s,
                NocPktType,
                CgraPayloadType,
                DataType,
                data_mem_size_global,
                data_mem_size_per_bank,
                num_banks_per_cgra = 4,
                num_wr_tiles = 4,
                multi_cgra_rows = 2,
                multi_cgra_columns = 2,
                num_tiles = 16,
                idTo2d_map = {0: [0, 0]},
                preload_data_per_bank = None):

    # Constant
    global_addr_nbits = clog2(data_mem_size_global)
    s.per_bank_addr_nbits = clog2(data_mem_size_per_bank)
    assert(2 ** global_addr_nbits == data_mem_size_global)
    assert(2 ** s.per_bank_addr_nbits == data_mem_size_per_bank)
    XType = mk_bits(max(clog2(multi_cgra_columns), 1))
    YType = mk_bits(max(clog2(multi_cgra_rows), 1))
    s.AddrType = mk_bits(global_addr_nbits)
    s.PerBankAddrType = mk_bits(s.per_bank_addr_nbits)
    s.num_banks_per_cgra = num_banks_per_cgra
    s.LocalBankIndexType = mk_bits(clog2(num_banks_per_cgra))
    s.num_wr_tiles = num_wr_tiles
    # The additional port is for the request from inter-cgra NoC via controller.
    num_xbar_in_wr_ports = num_wr_tiles + 1
    num_xbar_out_wr_ports = num_banks_per_cgra + 1
    s.num_cgras = multi_cgra_rows * multi_cgra_columns
    XbarOutWrType = mk_bits(clog2(num_xbar_out_wr_ports))
    TileSramXbarWrPktType = \
        mk_tile_sram_xbar_pkt(num_xbar_in_wr_ports,
                              num_xbar_out_wr_ports,
                              data_mem_size_global,
                              s.num_cgras,
                              num_tiles)

    # Interface
    # [num_rd_tiles] indicates the request from the NoC. ---> Add separate recv port for NoC.
    s.recv_from_noc_store_request = RecvIfcRTL(NocPktType)

    # [0, ..., num_rd_tiles - 1] indicate the requests from/to the tiles,
    s.recv_waddr = [RecvIfcRTL(s.AddrType) for _ in range(num_wr_tiles)]
    s.recv_wdata = [RecvIfcRTL(DataType) for _ in range(num_wr_tiles)]

    # Requests that targets remote SRAMs.
    s.send_to_noc_store_pkt = SendIfcRTL(NocPktType)

    # Component
    # As we include xbar and multi-bank for the memory hierarchy,
    # we prefer as few as possible number of ports.
    rd_ports_per_bank = 1
    wr_ports_per_bank = 1
    s.reg_file = [RegisterFile(DataType, data_mem_size_per_bank,
                               rd_ports_per_bank, wr_ports_per_bank)
                  for _ in range(num_banks_per_cgra)]
    # The additional 1 on inports indicates the read/write from NoC.
    # The additional 1 on outports indicates the request out of bound of
    # local memory space that would be forwarded to NoC.
    s.write_crossbar = XbarBypassQueueRTL(TileSramXbarWrPktType, num_xbar_in_wr_ports,
                                          num_xbar_out_wr_ports)
    s.initWrites = [[Wire(b1) for _ in range(data_mem_size_per_bank)]
                    for _ in range(num_banks_per_cgra)]
    s.init_mem_done = Wire(b1)
    s.init_mem_addr = Wire(s.PerBankAddrType)
    s.wr_pkt = [Wire(TileSramXbarWrPktType) for _ in range(num_xbar_in_wr_ports)]
    s.recv_wdata_bypass_q = [BypassQueueRTL(DataType, 1) for _ in range(num_xbar_in_wr_ports)]
    s.send_to_noc_load_pending = Wire(b1)
    s.cgra_id = InPort(mk_bits(max(1, clog2(s.num_cgras))))
    s.address_lower = InPort(s.AddrType)
    s.address_upper = InPort(s.AddrType)

    # Constructs the idTo2d lut.
    s.idTo2d_x_lut= [Wire(XType) for _ in range(multi_cgra_columns * multi_cgra_rows)]
    s.idTo2d_y_lut= [Wire(YType) for _ in range(multi_cgra_columns * multi_cgra_rows)]
    for cgra_id in idTo2d_map:
      xy = idTo2d_map[cgra_id]
      s.idTo2d_x_lut[cgra_id] //= XType(xy[0])
      s.idTo2d_y_lut[cgra_id] //= YType(xy[1])

    if preload_data_per_bank != None:
      preload_data_per_bank_size = data_mem_size_per_bank
      s.preload_data_per_bank = [[Wire(DataType) for _ in range(data_mem_size_per_bank)]
                                 for _ in range(num_banks_per_cgra)]
      for b in range(num_banks_per_cgra):
        for i in range(len(preload_data_per_bank[b])):
          s.preload_data_per_bank[b][i] //= preload_data_per_bank[b][i]
    else:
      preload_data_per_bank_size = 1
      s.preload_data_per_bank = [[Wire(DataType) for _ in range(preload_data_per_bank_size)]
                                 for _ in range(num_banks_per_cgra)]
      for b in range(num_banks_per_cgra):
        s.preload_data_per_bank[b][0] //= DataType()
    PreloadDataPerBankSizeType = mk_bits(max(1, clog2(preload_data_per_bank_size)))

    @update
    def assemble_xbar_wr_pkt():
      for i in range(num_xbar_in_wr_ports):
        s.wr_pkt[i] @= TileSramXbarWrPktType(i, 0, 0, 0, 0)

      if s.init_mem_done != b1(0):
        for i in range(num_wr_tiles):
          recv_waddr = s.recv_waddr[i].msg
          # Calculates the target bank index for store.
          if (recv_waddr >= s.address_lower) & (recv_waddr <= s.address_upper):
            bank_index_store_local = trunc((recv_waddr - s.address_lower) >> s.per_bank_addr_nbits, XbarOutWrType)
          else:
            bank_index_store_local = XbarOutWrType(num_banks_per_cgra)
          s.wr_pkt[i] @= TileSramXbarWrPktType(i,                       # src
                                               bank_index_store_local,  # dst
                                               recv_waddr,              # addr
                                               0,                       # src_cgra
                                               0)                       # src_tile

        recv_waddr_from_noc = s.recv_from_noc_store_request.msg.payload.data_addr
        if (recv_waddr_from_noc >= s.address_lower) & (recv_waddr_from_noc <= s.address_upper):
          bank_index_store_from_noc = trunc((recv_waddr_from_noc - s.address_lower) >> s.per_bank_addr_nbits, XbarOutWrType)
        else:
          bank_index_store_from_noc = XbarOutWrType(num_banks_per_cgra)
        s.wr_pkt[num_wr_tiles] @= TileSramXbarWrPktType(num_wr_tiles,               # src
                                                        bank_index_store_from_noc,  # dst
                                                        recv_waddr_from_noc,        # addr
                                                        0,                          # src_cgra
                                                        0)                          # src_tile

    @update
    def update_write():
      # Initializes write signals.
      for i in range(num_wr_tiles):
        s.recv_waddr[i].rdy @= 0
        s.recv_wdata_bypass_q[i].send.rdy @= 0
      s.recv_from_noc_store_request.rdy @= 0
      s.recv_wdata_bypass_q[num_wr_tiles].send.rdy @= 0

      for i in range(num_wr_tiles):
        s.recv_wdata[i].rdy @= 0
        s.recv_wdata_bypass_q[i].recv.val @= 0
        s.recv_wdata_bypass_q[i].recv.msg @= DataType()
      s.recv_wdata_bypass_q[num_wr_tiles].recv.val @= 0
      s.recv_wdata_bypass_q[num_wr_tiles].recv.msg @= DataType()
      
      s.send_to_noc_store_pkt.msg @= \
          NocPktType(0, # src
                     0, # dst
                     0, # src_x
                     0, # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # src_tile_id
                     0, # dst_tile_id
                     0, # opaque
                     0, # vc_id
                     CgraPayloadType(0, 0, 0, 0, 0))
      s.send_to_noc_store_pkt.val @= 0

      for i in range(num_xbar_in_wr_ports):
        s.write_crossbar.recv[i].val @= 0
        s.write_crossbar.recv[i].msg @= TileSramXbarWrPktType(0, 0, 0, 0, 0)

      for i in range(num_xbar_out_wr_ports):
        s.write_crossbar.send[i].rdy @= 0

      # Connects write xbar with the sram.
      if s.init_mem_done == 0:
        for b in range(num_banks_per_cgra):
          s.reg_file[b].waddr[0] @= trunc(s.init_mem_addr, s.PerBankAddrType)
          s.reg_file[b].wdata[0] @= s.preload_data_per_bank[b][trunc(s.init_mem_addr, PreloadDataPerBankSizeType)]
          s.reg_file[b].wen[0] @= b1(1)
      else:
        for i in range(num_wr_tiles):
          s.recv_wdata[i].rdy @= s.recv_wdata_bypass_q[i].recv.rdy
          s.recv_wdata_bypass_q[i].recv.val @= s.recv_wdata[i].val
          s.recv_wdata_bypass_q[i].recv.msg @= s.recv_wdata[i].msg
        s.recv_from_noc_store_request.rdy @= s.recv_wdata_bypass_q[num_wr_tiles].recv.rdy
        s.recv_wdata_bypass_q[num_wr_tiles].recv.val @= s.recv_from_noc_store_request.val
        s.recv_wdata_bypass_q[num_wr_tiles].recv.msg @= s.recv_from_noc_store_request.msg.payload.data

        for i in range(num_wr_tiles):
          s.write_crossbar.recv[i].val @= s.recv_waddr[i].val
          s.write_crossbar.recv[i].msg @= s.wr_pkt[i]
          s.recv_waddr[i].rdy @= s.write_crossbar.recv[i].rdy
        s.write_crossbar.recv[num_wr_tiles].val @= s.recv_from_noc_store_request.val
        s.write_crossbar.recv[num_wr_tiles].msg @= s.wr_pkt[num_wr_tiles]
        s.recv_from_noc_store_request.rdy @= s.write_crossbar.recv[num_wr_tiles].rdy

        # Connects the write ports towards SRAM and NoC from the xbar.
        for b in range(num_banks_per_cgra):
          s.reg_file[b].wen[0] @= b1(0)
          s.reg_file[b].waddr[0] @= trunc(s.write_crossbar.send[b].msg.addr % data_mem_size_per_bank, s.PerBankAddrType)
          s.reg_file[b].wdata[0] @= s.recv_wdata_bypass_q[s.write_crossbar.send[b].msg.src].send.msg
          s.write_crossbar.send[b].rdy @= 1
          s.reg_file[b].wen[0] @= s.write_crossbar.send[b].val

        for i in range(num_xbar_in_wr_ports):
          s.recv_wdata_bypass_q[i].send.rdy @= \
                  s.write_crossbar.send[s.write_crossbar.packet_on_input_units[i].dst].val

        # Handles the one connecting to the NoC.
        s.send_to_noc_store_pkt.msg @= \
            NocPktType(s.cgra_id, # src
                       0, # dst
                       s.idTo2d_x_lut[s.cgra_id], # src_x
                       s.idTo2d_y_lut[s.cgra_id], # src_y
                       0, # dst_x
                       0, # dst_y
                       0, # src_tile_id
                       0, # dst_tile_id
                       0, # opaque
                       0, # vc_id
                      CgraPayloadType(
                          CMD_STORE_REQUEST,
                          DataType(s.recv_wdata_bypass_q[s.write_crossbar.send[num_banks_per_cgra].msg.src].send.msg.payload,
                                   s.recv_wdata_bypass_q[s.write_crossbar.send[num_banks_per_cgra].msg.src].send.msg.predicate, 0, 0),
                          s.write_crossbar.send[num_banks_per_cgra].msg.addr, 0, 0))
        s.send_to_noc_store_pkt.val @= s.write_crossbar.send[num_banks_per_cgra].val
        s.write_crossbar.send[num_banks_per_cgra].rdy @= s.send_to_noc_store_pkt.rdy

    if preload_data_per_bank != None:
      # Preloads data.
      @update_ff
      def update_init_index_increment():
        if s.reset:
          s.init_mem_done <<= 0
          s.init_mem_addr <<= s.PerBankAddrType(0)
        else:
          if (s.init_mem_done == 0) & (s.init_mem_addr < data_mem_size_per_bank - 1):
            s.init_mem_addr <<= s.init_mem_addr + s.PerBankAddrType(1)
          else:
            s.init_mem_done <<= 1
            s.init_mem_addr <<= s.PerBankAddrType(0)

    else:
      @update_ff
      def update_init_index_once():
          if s.reset:
            s.init_mem_done <<= 0
            s.init_mem_addr <<= s.PerBankAddrType(0)
          else:
            if s.init_mem_done == 0:
              s.init_mem_done <<= 1
              s.init_mem_addr <<= s.PerBankAddrType(0)

