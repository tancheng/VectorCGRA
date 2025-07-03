"""
==========================================================================
DataMemWithCrossbarNbRTL.py
==========================================================================
Supplement read xbar and load related operations for non-blocking mode

Author : Yufei Yang
  Date : July 3, 2025
"""

from pymtl3.stdlib.primitive import RegisterFile

from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.basic.val_rdy.queues import BypassQueueRTL
from ...lib.messages import *
from ...noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL
from .DataMemWithCrossbarBasicRTL import DataMemWithCrossbarBasicRTL

class DataMemWithCrossbarNbRTL(DataMemWithCrossbarBasicRTL):

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
                preload_data_per_bank = None,
                NocPktType_NB = None,
                CgraPayloadType_NB = None,
                DataAddrType_NB = None):
                
    super(DataMemWithCrossbarNbRTL, s).construct( NocPktType,
						CgraPayloadType,
						DataType,
						data_mem_size_global,
						data_mem_size_per_bank,
						num_banks_per_cgra,
						num_wr_tiles,
						multi_cgra_rows,
						multi_cgra_columns,
						num_tiles,
						idTo2d_map,
						preload_data_per_bank)

    # Constant
    s.num_rd_tiles = num_rd_tiles
    RdTileIdType = mk_bits(clog2(num_rd_tiles))
    
    # The additional port is for the request from inter-cgra NoC via controller.
    num_xbar_in_rd_ports = num_rd_tiles + 1
    num_xbar_out_rd_ports = num_banks_per_cgra + 1
    XbarOutRdType = mk_bits(clog2(num_xbar_out_rd_ports))
    TileSramXbarRdPktType = \
          mk_tile_sram_xbar_pkt(num_xbar_in_rd_ports,
                                  num_xbar_out_rd_ports,
                                  data_mem_size_global,
                                  s.num_cgras,
                                  num_tiles, non_blocking=True)
    # Interface
    # [num_rd_tiles] indicates the request from the NoC. ---> Add separate recv port for NoC.
    s.recv_from_noc_load_request = RecvIfcRTL(NocPktType_NB)

    # [0, ..., num_rd_tiles - 1] indicate the requests from/to the tiles,
    s.recv_raddr = [RecvIfcRTL(DataAddrType_NB) for _ in range(num_rd_tiles)]
    s.send_rdata = [SendIfcRTL(DataType) for _ in range(num_rd_tiles)]
    
    s.send_to_noc_load_response_pkt = SendIfcRTL(NocPktType_NB)

    # Response that is from a remote SRAM.
    s.recv_from_noc_load_response_pkt = RecvIfcRTL(NocPktType_NB)

    # Requests that targets remote SRAMs.
    s.send_to_noc_load_request_pkt = SendIfcRTL(NocPktType_NB)

    # Lookuptable for nonblocking execution mode, exist anyway
    s.recv_from_noc_buffer = [RegisterFile(DataType, nregs=32, rd_ports=num_banks_per_cgra, wr_ports=2) for _ in range(4)]

    # Component
    s.read_crossbar = XbarBypassQueueRTL(TileSramXbarRdPktType, num_xbar_in_rd_ports,
                                         num_xbar_out_rd_ports)
    s.rd_pkt = [Wire(TileSramXbarRdPktType) for _ in range(num_xbar_in_rd_ports)]

    @update
    def assemble_xbar_rd_pkt():
      for i in range(num_xbar_in_rd_ports):
        s.rd_pkt[i] @= TileSramXbarRdPktType(i, 0, 0, 0, 0)

      if s.init_mem_done != b1(0):
        for i in range(num_rd_tiles):
          recv_raddr = s.recv_raddr[i].msg.addr
          # Calculates the target bank index for load.
          if (recv_raddr >= s.address_lower) & (recv_raddr <= s.address_upper):
            bank_index_load_local = trunc((recv_raddr - s.address_lower) >> s.per_bank_addr_nbits, XbarOutRdType)
          else:
            bank_index_load_local = XbarOutRdType(num_banks_per_cgra)
          # FIXME: change to exact tile id.
          s.rd_pkt[i] @= TileSramXbarRdPktType(i,                       # src
                                               bank_index_load_local,   # dst
                                               recv_raddr,              # addr
                                               s.cgra_id,               # src_cgra
                                               0,                       # src_tile
                                               s.recv_raddr[i].msg.kernel_id, # kernel_id
                                               s.recv_raddr[i].msg.ld_id) # ld_id 

        recv_raddr_from_noc = s.recv_from_noc_load_request.msg.payload.data_addr.addr
        # Calculates the target bank index.
        if (recv_raddr_from_noc >= s.address_lower) & (recv_raddr_from_noc <= s.address_upper):
          bank_index_load_from_noc = trunc((recv_raddr_from_noc - s.address_lower) >> s.per_bank_addr_nbits, XbarOutRdType)
        else:
          bank_index_load_from_noc = XbarOutRdType(num_banks_per_cgra)
        s.rd_pkt[num_rd_tiles] @= TileSramXbarRdPktType(num_rd_tiles,                                   # src
                                                        bank_index_load_from_noc,                       # dst
                                                        recv_raddr_from_noc,                            # addr
                                                        s.recv_from_noc_load_request.msg.src,           # src_cgra
                                                        s.recv_from_noc_load_request.msg.src_tile_id,   # src_tile
                                                        s.recv_from_noc_load_request.msg.payload.data_addr.kernel_id, # kernel_id
                                                        s.recv_from_noc_load_request.msg.payload.data_addr.ld_id) # ld_id

    @update
    def update_read():
      # Initializes read signals.
      for i in range(num_rd_tiles):
        s.recv_raddr[i].rdy @= 0
      s.recv_from_noc_load_request.rdy @= 0

      for i in range(num_rd_tiles):
        s.send_rdata[i].val @= 0
        s.send_rdata[i].msg @= DataType()
      s.send_to_noc_load_response_pkt.val @= 0
      
      s.send_to_noc_load_response_pkt.msg @= \
          NocPktType_NB(0, # src
                     0, # dst
                     0, # src_x
                     0, # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # src_tile_id
                     0, # dst_tile_id
                     0, # opaque
                     0, # vc_id
                     CgraPayloadType_NB(0, 0, 0, 0, 0))

      for i in range(num_xbar_in_rd_ports):
        s.read_crossbar.recv[i].val @= 0
        s.read_crossbar.recv[i].msg @= TileSramXbarRdPktType(0, 0, 0, 0, 0)

      s.recv_from_noc_load_response_pkt.rdy @= 0
      
      for i in range(num_xbar_out_rd_ports):
        s.read_crossbar.send[i].rdy @= 0

      for b in range(num_banks_per_cgra):
        s.reg_file[b].raddr[0] @= s.PerBankAddrType(0)

      s.send_to_noc_load_request_pkt.msg @= \
          NocPktType_NB(0, # src
                     0, # dst
                     0, # src_x
                     0, # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # src_tile_id
                     0, # dst_tile_id
                     0, # opaque
                     0, # vc_id
                     CgraPayloadType_NB(0, 0, 0, 0, 0))

      s.send_to_noc_load_request_pkt.val @= 0

      # Connects read xbar with the sram.
      if s.init_mem_done == 0:
        pass
      else:
        for i in range(num_rd_tiles):
            s.read_crossbar.recv[i].val @= s.recv_raddr[i].val
            s.read_crossbar.recv[i].msg @= s.rd_pkt[i]
            s.recv_raddr[i].rdy @= s.read_crossbar.recv[i].rdy
        s.read_crossbar.recv[num_rd_tiles].val @= s.recv_from_noc_load_request.val
        s.read_crossbar.recv[num_rd_tiles].msg @= s.rd_pkt[num_rd_tiles]
        s.recv_from_noc_load_request.rdy @= s.read_crossbar.recv[num_rd_tiles].rdy

        # Connects the read ports towards SRAM and NoC from the xbar.
        for b in range(num_banks_per_cgra):
          s.read_crossbar.send[b].rdy @= 1
          s.reg_file[b].raddr[0] @= trunc(s.read_crossbar.send[b].msg.addr % data_mem_size_per_bank, s.PerBankAddrType)

        for i in range(num_xbar_in_rd_ports):
          if (s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src == i) & \
             (s.read_crossbar.packet_on_input_units[i].dst < num_banks_per_cgra):
            if i < num_rd_tiles:
              s.send_rdata[RdTileIdType(i)].msg @= s.reg_file[trunc(s.read_crossbar.packet_on_input_units[i].dst, s.LocalBankIndexType)].rdata[0]
              s.send_rdata[RdTileIdType(i)].val @= s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].val
            # TODO: Check the translated Verilog to make sure the loop is flattened correctly with special out (NocPktType) towards NoC.
            else:
              from_cgra_id = s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src_cgra
              from_tile_id = s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src_tile
              addr = DataAddrType_NB(s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.addr,
                                       s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.kernel_id,
                                       s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.ld_id)
              s.send_to_noc_load_response_pkt.msg @= \
                  NocPktType_NB(
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
                      CgraPayloadType_NB(
                          CMD_LOAD_RESPONSE,
                          DataType(s.reg_file[trunc(s.read_crossbar.packet_on_input_units[i].dst, s.LocalBankIndexType)].rdata[0].payload,
                                   s.reg_file[trunc(s.read_crossbar.packet_on_input_units[i].dst, s.LocalBankIndexType)].rdata[0].predicate, 0, 0),
                                   addr, 0, 0))

              s.send_to_noc_load_response_pkt.val @= \
                  s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].val

          # Handles the case the load requests coming from a remote CGRA via the NoC.
          elif (s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.src == i) & \
               (s.read_crossbar.packet_on_input_units[i].dst >= num_banks_per_cgra):
            kernel_id = s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.kernel_id
            ld_id = s.read_crossbar.send[s.read_crossbar.packet_on_input_units[i].dst].msg.ld_id
            # get requested data from s.recv_from_noc_buffer
            s.recv_from_noc_buffer[kernel_id].raddr[RdTileIdType(i)] @= ld_id
            s.send_rdata[RdTileIdType(i)].msg.payload @= s.recv_from_noc_buffer[kernel_id].rdata[RdTileIdType(i)].payload
            s.send_rdata[RdTileIdType(i)].msg.predicate @= s.recv_from_noc_buffer[kernel_id].rdata[RdTileIdType(i)].predicate
            s.send_rdata[RdTileIdType(i)].val @= 1
            # if predicate = 1, reset the place at next clock cycle
            # to get ready for the next remote CGRA memory access
            if s.recv_from_noc_buffer[kernel_id].rdata[RdTileIdType(i)].predicate:
              s.recv_from_noc_buffer[kernel_id].waddr[1] @= ld_id
              #                                                      payload predicate
              s.recv_from_noc_buffer[kernel_id].wdata[1] @= DataType(0,      0)
              s.recv_from_noc_buffer[kernel_id].wen[1] @= 1

        # Handles the request (not response) towards the others via the NoC.
        addr = DataAddrType_NB(s.read_crossbar.send[num_banks_per_cgra].msg.addr,
                                 s.read_crossbar.send[num_banks_per_cgra].msg.kernel_id,
                                 s.read_crossbar.send[num_banks_per_cgra].msg.ld_id)
        s.send_to_noc_load_request_pkt.msg @= \
            NocPktType_NB(s.cgra_id, # src
                       0, # dst
                       s.idTo2d_x_lut[s.cgra_id], # src_x
                       s.idTo2d_y_lut[s.cgra_id], # src_y
                       0, # dst_x
                       0, # dst_y
                       0, # src_tile_id
                       0, # dst_tile_id
                       0, # opaque
                       0, # vc_id
                       CgraPayloadType_NB(
                           CMD_LOAD_REQUEST,
                           0,
                           addr, 0, 0))

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
        s.recv_from_noc_load_response_pkt.rdy @= 1
        # Only allows releasing the pending request until the required load data is back,
        # i.e., though the request already sent out to NoC (the port is still blocked until
        # response is back).
        s.read_crossbar.send[num_banks_per_cgra].rdy @= 1

        # Handles recv_from_noc_load_response_pkt, connect it directly to the recv_from_noc_buffer.
        remote_access_kernel_id = s.recv_from_noc_load_response_pkt.msg.payload.data_addr.kernel_id
        remote_access_ld_id = s.recv_from_noc_load_response_pkt.msg.payload.data_addr.ld_id
        s.recv_from_noc_buffer[remote_access_kernel_id].waddr[0] @= remote_access_ld_id
        s.recv_from_noc_buffer[remote_access_kernel_id].wdata[0] @= s.recv_from_noc_load_response_pkt.msg.payload.data
        s.recv_from_noc_buffer[remote_access_kernel_id].wen[0] @= s.recv_from_noc_load_response_pkt.val
        s.recv_from_noc_load_response_pkt.rdy @= 1
      
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
   

