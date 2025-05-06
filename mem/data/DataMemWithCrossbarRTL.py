"""
==========================================================================
DataMemWithCrossbarRTL.py
==========================================================================
Data memory for CGRA. It has addtional port to connect to controller,
which can be used for multi-CGRA fabric.
 - Send/recv data request/response to/from other CGRA controllers.
   - Based on whether the target data address is within the local space.
   - Coherence is not targeted for now; protyping in static memory space.
 - Send/recv cmd request/response to/from other CGRA controllers.
   - E.g., dynamic rescheduling.
   - The cmd can be originally derived from a runtime scheduler.

In addition, it contains a crossbar to handle multi-bank conflicts.
 - Crossbar contains an arbitor, i.e., stall may happen on certain port.
   - Therefore, bypass queue is leveraged on the input port.
 - [ ] https://github.com/tancheng/VectorCGRA/issues/26:
     Blocking vs. non-blocking should be configured/propagated here.
   - Non-blocking:
     - Immediate return data though it is not ready:
       - Bank conflicted lower priority access.
       - Remote accessed data.
   - Blocking and non-blocking might be configurabled in a dynamic way.

Author : Cheng Tan
  Date : Dec 5, 2024
"""

from pymtl3.stdlib.primitive import RegisterFile

from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.basic.val_rdy.queues import BypassQueueRTL
from ...lib.messages import *
from ...noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL


class DataMemWithCrossbarRTL(Component):

  def construct(s,
                NocPktType,
                CgraPayloadType,
                DataType,
                data_mem_size_global,
                data_mem_size_per_bank,
                num_banks_per_cgra = 4,
                num_rd_tiles = 4,
                num_wr_tiles = 4,
                multi_cgra_rows = 2,
                multi_cgra_columns = 2,
                num_tiles = 16,
                idTo2d_map = {0: [0, 0]},
                preload_data_per_bank = None):

    # Constant
    global_addr_nbits = clog2(data_mem_size_global)
    per_bank_addr_nbits = clog2(data_mem_size_per_bank)
    assert(2 ** global_addr_nbits == data_mem_size_global)
    assert(2 ** per_bank_addr_nbits == data_mem_size_per_bank)
    XType = mk_bits(max(clog2(multi_cgra_columns), 1))
    YType = mk_bits(max(clog2(multi_cgra_rows), 1))
    AddrType = mk_bits(global_addr_nbits)
    PerBankAddrType = mk_bits(per_bank_addr_nbits)
    s.num_banks_per_cgra = num_banks_per_cgra
    LocalBankIndexType = mk_bits(clog2(num_banks_per_cgra))
    s.num_rd_tiles = num_rd_tiles
    s.num_wr_tiles = num_wr_tiles
    RdTileIdType = mk_bits(clog2(num_rd_tiles))
    # The additional port is for the request from inter-cgra NoC via controller.
    num_xbar_in_rd_ports = num_rd_tiles + 1
    num_xbar_in_wr_ports = num_wr_tiles + 1
    num_xbar_out_rd_ports = num_banks_per_cgra + 1
    num_xbar_out_wr_ports = num_banks_per_cgra + 1
    num_cgras = multi_cgra_rows * multi_cgra_columns
    XbarOutRdType = mk_bits(clog2(num_xbar_out_rd_ports))
    XbarOutWrType = mk_bits(clog2(num_xbar_out_wr_ports))
    TileSramXbarRdPktType = \
        mk_tile_sram_xbar_pkt(num_xbar_in_rd_ports,
                              num_xbar_out_rd_ports,
                              data_mem_size_global,
                              num_cgras,
                              num_tiles)
    TileSramXbarWrPktType = \
        mk_tile_sram_xbar_pkt(num_xbar_in_wr_ports,
                              num_xbar_out_wr_ports,
                              data_mem_size_global,
                              num_cgras,
                              num_tiles)


    # Interface
    # [num_rd_tiles] indicates the request from the NoC. ---> Add separate recv port for NoC.
    s.recv_from_noc_load_request = RecvIfcRTL(NocPktType)
    s.recv_from_noc_store_request = RecvIfcRTL(NocPktType)

    # [0, ..., num_rd_tiles - 1] indicate the requests from/to the tiles,
    s.recv_raddr = [RecvIfcRTL(AddrType) for _ in range(num_rd_tiles)]
    s.recv_waddr = [RecvIfcRTL(AddrType) for _ in range(num_wr_tiles)]
    s.recv_wdata = [RecvIfcRTL(DataType) for _ in range(num_wr_tiles)]


    s.send_rdata = [SendIfcRTL(DataType) for _ in range(num_rd_tiles)]

    s.send_to_noc_load_response_pkt = SendIfcRTL(NocPktType)

    # Response that is from a remote SRAM.
    s.recv_from_noc_load_response_pkt = RecvIfcRTL(NocPktType)

    # Requests that targets remote SRAMs.
    s.send_to_noc_load_request_pkt = SendIfcRTL(NocPktType)
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
    s.read_crossbar = XbarBypassQueueRTL(TileSramXbarRdPktType, num_xbar_in_rd_ports,
                                         num_xbar_out_rd_ports)
    s.write_crossbar = XbarBypassQueueRTL(TileSramXbarWrPktType, num_xbar_in_wr_ports,
                                          num_xbar_out_wr_ports)
    s.initWrites = [[Wire(b1) for _ in range(data_mem_size_per_bank)]
                    for _ in range(num_banks_per_cgra)]
    s.init_mem_done = Wire(b1)
    s.init_mem_addr = Wire(PerBankAddrType)

    s.rd_pkt = [Wire(TileSramXbarRdPktType) for _ in range(num_xbar_in_rd_ports)]
    s.wr_pkt = [Wire(TileSramXbarWrPktType) for _ in range(num_xbar_in_wr_ports)]

    s.recv_wdata_bypass_q = [BypassQueueRTL(DataType, 1) for _ in range(num_xbar_in_wr_ports)]

    s.send_to_noc_load_pending = Wire(b1)

    s.cgra_id = InPort(mk_bits(max(1, clog2(num_cgras))))

    s.address_lower = InPort(AddrType)
    s.address_upper = InPort(AddrType)

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
    def assemble_xbar_pkt():
      for i in range(num_xbar_in_rd_ports):
        s.rd_pkt[i] @= TileSramXbarRdPktType(i, 0, 0, 0, 0)

      for i in range(num_xbar_in_wr_ports):
        s.wr_pkt[i] @= TileSramXbarWrPktType(i, 0, 0, 0, 0)

      if s.init_mem_done != b1(0):
        for i in range(num_rd_tiles):
          recv_raddr = s.recv_raddr[i].msg
          # Calculates the target bank index for load.
          if (recv_raddr >= s.address_lower) & (recv_raddr <= s.address_upper):
            bank_index_load_local = trunc((recv_raddr - s.address_lower) >> per_bank_addr_nbits, XbarOutRdType)
          else:
            bank_index_load_local = XbarOutRdType(num_banks_per_cgra)
          # FIXME: change to exact tile id.
          s.rd_pkt[i] @= TileSramXbarRdPktType(i, bank_index_load_local, recv_raddr, s.cgra_id, 0)

        recv_raddr_from_noc = s.recv_from_noc_load_request.msg.payload.data_addr
        # Calculates the target bank index.
        if (recv_raddr_from_noc >= s.address_lower) & (recv_raddr_from_noc <= s.address_upper):
          bank_index_load_from_noc = trunc((recv_raddr_from_noc - s.address_lower) >> per_bank_addr_nbits, XbarOutRdType)
        else:
          bank_index_load_from_noc = XbarOutRdType(num_banks_per_cgra)
        s.rd_pkt[num_rd_tiles] @= TileSramXbarRdPktType(num_rd_tiles, bank_index_load_from_noc, recv_raddr_from_noc, s.recv_from_noc_load_request.msg.src, s.recv_from_noc_load_request.msg.src_tile_id)

        for i in range(num_wr_tiles):
          recv_waddr = s.recv_waddr[i].msg
          # Calculates the target bank index for store.
          if (recv_waddr >= s.address_lower) & (recv_waddr <= s.address_upper):
            bank_index_store_local = trunc((recv_waddr - s.address_lower) >> per_bank_addr_nbits, XbarOutWrType)
          else:
            bank_index_store_local = XbarOutWrType(num_banks_per_cgra)
          s.wr_pkt[i] @= TileSramXbarWrPktType(i, bank_index_store_local, recv_waddr, 0, 0)

        recv_waddr_from_noc = s.recv_from_noc_store_request.msg.payload.data_addr
        if (recv_waddr_from_noc >= s.address_lower) & (recv_waddr_from_noc <= s.address_upper):
          bank_index_store_from_noc = trunc((recv_waddr_from_noc - s.address_lower) >> per_bank_addr_nbits, XbarOutWrType)
        else:
          bank_index_store_from_noc = XbarOutWrType(num_banks_per_cgra)
        s.wr_pkt[num_wr_tiles] @= TileSramXbarWrPktType(num_wr_tiles, bank_index_store_from_noc, recv_waddr_from_noc, 0, 0)


    # Connects xbar with the sram.
    @update
    def update_all():

      # Initializes the signals.
      for i in range(num_rd_tiles):
          s.recv_raddr[i].rdy @= 0
      s.recv_from_noc_load_request.rdy @= 0

      for i in range(num_wr_tiles):
        s.recv_waddr[i].rdy @= 0
        s.recv_wdata_bypass_q[i].send.rdy @= 0
      s.recv_from_noc_store_request.rdy @= 0
      s.recv_wdata_bypass_q[num_wr_tiles].send.rdy @= 0

      for i in range(num_rd_tiles):
        s.send_rdata[i].val @= 0
        s.send_rdata[i].msg @= DataType()
      s.send_to_noc_load_response_pkt.val @= 0

      s.send_to_noc_load_response_pkt.msg @= \
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

      for i in range(num_xbar_in_rd_ports):
        s.read_crossbar.recv[i].val @= 0
        s.read_crossbar.recv[i].msg @= TileSramXbarRdPktType(0, 0, 0, 0, 0)

      s.recv_from_noc_load_response_pkt.rdy @= 0

      for i in range(num_xbar_in_wr_ports):
        s.write_crossbar.recv[i].val @= 0
        s.write_crossbar.recv[i].msg @= TileSramXbarRdPktType(0, 0, 0, 0, 0)

      for i in range(num_xbar_out_wr_ports):
        s.write_crossbar.send[i].rdy @= 0

      for i in range(num_xbar_out_rd_ports):
        s.read_crossbar.send[i].rdy @= 0

      for b in range(num_banks_per_cgra):
        s.reg_file[b].raddr[0] @= PerBankAddrType(0)

      s.send_to_noc_load_request_pkt.msg @= \
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

      s.send_to_noc_load_request_pkt.val @= 0

      if s.init_mem_done == 0:
        for b in range(num_banks_per_cgra):
          s.reg_file[b].waddr[0] @= trunc(s.init_mem_addr, PerBankAddrType)
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

        for i in range(num_rd_tiles):
            s.read_crossbar.recv[i].val @= s.recv_raddr[i].val
            s.read_crossbar.recv[i].msg @= s.rd_pkt[i]
            s.recv_raddr[i].rdy @= s.read_crossbar.recv[i].rdy
        s.read_crossbar.recv[num_rd_tiles].val @= s.recv_from_noc_load_request.val
        s.read_crossbar.recv[num_rd_tiles].msg @= s.rd_pkt[num_rd_tiles]
        s.recv_from_noc_load_request.rdy @= s.read_crossbar.recv[num_rd_tiles].rdy

        for i in range(num_wr_tiles):
          s.write_crossbar.recv[i].val @= s.recv_waddr[i].val
          s.write_crossbar.recv[i].msg @= s.wr_pkt[i]
          s.recv_waddr[i].rdy @= s.write_crossbar.recv[i].rdy
        s.write_crossbar.recv[num_wr_tiles].val @= s.recv_from_noc_store_request.val
        s.write_crossbar.recv[num_wr_tiles].msg @= s.wr_pkt[num_wr_tiles]
        s.recv_from_noc_store_request.rdy @= s.write_crossbar.recv[num_wr_tiles].rdy

        # Connects the read ports towards SRAM and NoC from the xbar.
        for b in range(num_banks_per_cgra):
          s.read_crossbar.send[b].rdy @= 1
          s.reg_file[b].raddr[0] @= trunc(s.read_crossbar.send[b].msg.addr % data_mem_size_per_bank, PerBankAddrType)

        for i in range(num_xbar_in_rd_ports):
          if (s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src == i) & \
             (s.read_crossbar.packet_on_input_units[i].dst < num_banks_per_cgra):
            if i < num_rd_tiles:
              s.send_rdata[RdTileIdType(i)].msg @= s.reg_file[trunc(s.read_crossbar.packet_on_input_units[i].dst, LocalBankIndexType)].rdata[0]
              s.send_rdata[RdTileIdType(i)].val @= s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].val
            # TODO: Check the translated Verilog to make sure the loop is flattened correctly with special out (NocPktType) towards NoC.
            else:
              from_cgra_id = s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src_cgra
              from_tile_id = s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src_tile
              s.send_to_noc_load_response_pkt.msg @= \
                  NocPktType(
                      s.cgra_id, # src_cgra_id
                      from_cgra_id, # dst_cgra_id
                      s.idTo2d_x_lut[s.cgra_id], # src_cgra_x
                      s.idTo2d_y_lut[s.cgra_id], # src_cgra_y
                      s.idTo2d_x_lut[from_cgra_id], # dst_cgra_x
                      s.idTo2d_y_lut[from_cgra_id], # dst_cgra_x
                      0, # src_tile_id
                      s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src_tile, # dst_tile_id
                      0, # opaque
                      0, # vc_id
                      CgraPayloadType(
                          CMD_LOAD_RESPONSE,
                          DataType(s.reg_file[trunc(s.read_crossbar.packet_on_input_units[i].dst, LocalBankIndexType)].rdata[0].payload,
                                   s.reg_file[trunc(s.read_crossbar.packet_on_input_units[i].dst, LocalBankIndexType)].rdata[0].predicate, 0, 0),
                          s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.addr, 0, 0))

              s.send_to_noc_load_response_pkt.val @= \
                  s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].val

          # Handles the case the load requests coming from a remote CGRA via the NoC.
          elif (s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src == i) & \
               (s.read_crossbar.packet_on_input_units[i].dst >= num_banks_per_cgra):
            # Request from NoC would never target another remote access, i.e., as long
            # as the request can come from the NoC, it meant to access this local SRAM,
            # which should be guarded by the controller and NoC routers.
            # assert(i < num_banks_per_cgra)
            s.send_rdata[RdTileIdType(i)].msg @= s.recv_from_noc_load_response_pkt.msg.payload.data
            # TODO: https://github.com/tancheng/VectorCGRA/issues/26 -- Modify this part for non-blocking access.
            s.send_rdata[RdTileIdType(i)].val @= \
                s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].val & \
                s.recv_from_noc_load_response_pkt.val
                # FIXME: The msg would come back one by one in order, so no
                # need to check the src_tile, which can be improved.
                # s.recv_from_noc_rdata.en & \
                # (s.recv_from_noc_rdata.msg.src_tile == i)

        # Handles the request (not response) towards the others via the NoC.
        s.send_to_noc_load_request_pkt.msg @= \
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
                           CMD_LOAD_REQUEST,
                           0,
                           s.read_crossbar.send[num_banks_per_cgra].msg.addr, 0, 0))

        # 'send_to_noc_load_pending' avoids sending pending request multiple times.
        s.send_to_noc_load_request_pkt.val @= s.read_crossbar.send[num_banks_per_cgra].val & \
                                              ~s.send_to_noc_load_pending
                                              # s.recv_from_noc_rdata.val
                                              # s.send_to_noc_load_request_pkt.rdy & \
        # Outstanding remote read access would block the inport (for read request) of the NoC. 
        # Therefore, we don't have to include `& s.send_rdata[x].rdy` as it must be ready/pending
        # for a long time waiting for the response.
        # TODO: https://github.com/tancheng/VectorCGRA/issues/26 -- Modify this part for non-blocking access.
        # 'val` indicates the data is arbitrated successfully.
        s.recv_from_noc_load_response_pkt.rdy @= s.read_crossbar.send[num_banks_per_cgra].val
        # Only allows releasing the pending request until the required load data is back,
        # i.e., though the request already sent out to NoC (the port is still blocked until
        # response is back).
        s.read_crossbar.send[num_banks_per_cgra].rdy @= s.recv_from_noc_load_response_pkt.val

        # Connects the write ports towards SRAM and NoC from the xbar.
        for b in range(num_banks_per_cgra):
          s.reg_file[b].wen[0] @= b1(0)
          s.reg_file[b].waddr[0] @= trunc(s.write_crossbar.send[b].msg.addr % data_mem_size_per_bank, PerBankAddrType)
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
          s.init_mem_addr <<= PerBankAddrType(0)
        else:
          if (s.init_mem_done == 0) & (s.init_mem_addr < data_mem_size_per_bank - 1):
            s.init_mem_addr <<= s.init_mem_addr + PerBankAddrType(1)
          else:
            s.init_mem_done <<= 1
            s.init_mem_addr <<= PerBankAddrType(0)

    else:
      @update_ff
      def update_init_index_once():
          if s.reset:
            s.init_mem_done <<= 0
            s.init_mem_addr <<= PerBankAddrType(0)
          else:
            if s.init_mem_done == 0:
              s.init_mem_done <<= 1
              s.init_mem_addr <<= PerBankAddrType(0)

    # Indicates whether the remote (towards others via NoC) load is pending on response.
    @update_ff
    def update_remote_load_pending():
      if s.reset:
        s.send_to_noc_load_pending <<= 0
      else:
        if s.recv_from_noc_load_response_pkt.val:
          s.send_to_noc_load_pending <<= 0
        elif s.send_to_noc_load_request_pkt.val & s.send_to_noc_load_request_pkt.rdy:
          s.send_to_noc_load_pending <<= 1

  def line_trace(s):
    recv_raddr_str = "recv_from_tile_read_addr: {"
    recv_waddr_str = "recv_from_tile_write_addr: {"
    recv_wdata_str = "recv_from_tile_write_data: {"
    content_str = "content: {"
    send_rdata_str = "send_to_tile_read_data: {"

    send_to_noc_load_request_pkt_str = "send_to_noc_load_request_pkt: {"
    send_to_noc_load_response_pkt_str = "send_to_noc_load_response_pkt: {"
    recv_from_noc_load_response_pkt_str = "recv_from_noc_load_response_pkt: {"
    send_to_noc_store_pkt_str = "send_to_noc_store_pkt: {"


    for b in range(s.num_banks_per_cgra):
      recv_raddr_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.recv_raddr]) + ";"
      recv_waddr_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.recv_waddr]) + ";"
      recv_wdata_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.recv_wdata]) + ";"
      content_str +=  " bank[" + str(b) + "]: " + "|".join([str(data) for data in s.reg_file[b].regs]) + ";"
      send_rdata_str += " bank[" + str(b) + "]: " + "|".join([str(data.msg) for data in s.send_rdata]) + ";"

    send_to_noc_load_request_pkt_str += str(s.send_to_noc_load_request_pkt.msg) + ";"
    send_to_noc_load_response_pkt_str += " " + str(s.send_to_noc_load_response_pkt.msg) + " "
    recv_from_noc_load_response_pkt_str += str(s.recv_from_noc_load_response_pkt.msg) + ";"
    send_to_noc_store_pkt_str += str(s.send_to_noc_store_pkt.msg) + ", val: " + str(s.send_to_noc_store_pkt.val) + ";"

    recv_raddr_str += "}"
    send_rdata_str += "}"
    recv_waddr_str += "}"
    recv_wdata_str += "}"
    send_to_noc_load_request_pkt_str += "}"
    send_to_noc_load_response_pkt_str += "}"
    recv_from_noc_load_response_pkt_str += "}"
    send_to_noc_store_pkt_str += "}"
    read_crossbar_str = "read_crossbar: " + s.read_crossbar.line_trace()
    write_crossbar_str = "write_crossbar: " + s.write_crossbar.line_trace()
    content_str += "}"

    return f'{recv_raddr_str} || {recv_waddr_str} || {recv_wdata_str} || {send_rdata_str} || {send_to_noc_load_request_pkt_str} || {send_to_noc_load_response_pkt_str} || {recv_from_noc_load_response_pkt_str} || {send_to_noc_store_pkt_str} || {read_crossbar_str} || {write_crossbar_str} || [{content_str}]'

