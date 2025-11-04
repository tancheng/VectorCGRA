"""
==========================================================================
DataMemControllerRTL.py
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
  Date : Aug 28, 2025
"""

from .DataMemWrapperRTL import DataMemWrapperRTL
from ...lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ...lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ...lib.messages import *
from ...noc.PyOCN.pymtl3_net.xbar.XbarBypassQueueRTL import XbarBypassQueueRTL
from ...lib.util.data_struct_attr import *

class DataMemControllerRTL(Component):
  def construct(s,
                NocPktType,
                data_mem_size_global,
                data_mem_size_per_bank,
                num_banks_per_cgra = 4,
                num_rd_tiles = 4,
                num_wr_tiles = 4,
                multi_cgra_rows = 2,
                multi_cgra_columns = 2,
                num_tiles = 16,
                mem_access_is_combinational = True,
                idTo2d_map = {0: [0, 0]}):

    CgraPayloadType = NocPktType.get_field_type(kAttrPayload)
    DataType = CgraPayloadType.get_field_type(kAttrData)
    # Constants.
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
    MemReadPktType = \
        mk_mem_access_pkt(DataType,
                          num_xbar_in_rd_ports,
                          num_xbar_out_rd_ports,
                          data_mem_size_global,
                          num_cgras,
                          num_tiles,
                          num_rd_tiles)
    MemWritePktType = \
        mk_mem_access_pkt(DataType,
                          num_xbar_in_wr_ports,
                          num_xbar_out_wr_ports,
                          data_mem_size_global,
                          num_cgras,
                          num_tiles,
                          num_rd_tiles)

    # Reverses the source and destination for response packet.
    MemResponsePktType = \
        mk_mem_access_pkt(DataType,
                          num_xbar_out_rd_ports,
                          num_xbar_in_rd_ports,
                          data_mem_size_global,
                          num_cgras,
                          num_tiles,
                          num_rd_tiles)

    # Interfaces.
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

    # Components.
    s.memory_wrapper = [DataMemWrapperRTL(DataType, MemReadPktType, MemWritePktType, MemResponsePktType,
                                          data_mem_size_global, data_mem_size_per_bank, mem_access_is_combinational)
                  for _ in range(num_banks_per_cgra)]
    # The additional 1 on inports indicates the read/write from NoC.
    # The additional 1 on outports indicates the request out of bound of
    # local memory space that would be forwarded to NoC.
    s.read_crossbar = XbarBypassQueueRTL(MemReadPktType, num_xbar_in_rd_ports,
                                         num_xbar_out_rd_ports)
    s.write_crossbar = XbarBypassQueueRTL(MemWritePktType, num_xbar_in_wr_ports,
                                          num_xbar_out_wr_ports)
    s.response_crossbar = XbarBypassQueueRTL(MemResponsePktType, num_xbar_out_rd_ports,
                                             num_xbar_in_rd_ports)

    s.rd_pkt = [Wire(MemReadPktType) for _ in range(num_xbar_in_rd_ports)]
    s.wr_pkt = [Wire(MemWritePktType) for _ in range(num_xbar_in_wr_ports)]

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

    # Connections.
    for i in range(num_banks_per_cgra):
      s.read_crossbar.send[i] //= s.memory_wrapper[i].recv_rd
      s.write_crossbar.send[i] //= s.memory_wrapper[i].recv_wr
      s.memory_wrapper[i].send //= s.response_crossbar.recv[i]

    @update
    def assemble_xbar_pkt():
      for i in range(num_xbar_in_rd_ports):
        s.rd_pkt[i] @= MemReadPktType(i, 0, 0, DataType(0, 0, 0, 0), 0, 0, i)

      for i in range(num_xbar_in_wr_ports):
        s.wr_pkt[i] @= MemWritePktType(i, 0, 0, DataType(0, 0, 0, 0), 0, 0, i)

      for i in range(num_rd_tiles):
        recv_raddr = s.recv_raddr[i].msg
        # Calculates the target bank index for load.
        if (recv_raddr >= s.address_lower) & (recv_raddr <= s.address_upper):
          bank_index_load_local = trunc((recv_raddr - s.address_lower) >> per_bank_addr_nbits, XbarOutRdType)
        else:
          bank_index_load_local = XbarOutRdType(num_banks_per_cgra)
        # FIXME: change to exact tile id.
        s.rd_pkt[i] @= MemReadPktType(i,                       # src
                                      bank_index_load_local,   # dst
                                      recv_raddr,              # addr
                                      DataType(0, 0, 0, 0),    # data
                                      s.cgra_id,               # src_cgra
                                      0,                       # src_tile
                                      i)                       # remote_src_port

      recv_raddr_from_noc = s.recv_from_noc_load_request.msg.payload.data_addr
      # Calculates the target bank index.
      if (recv_raddr_from_noc >= s.address_lower) & (recv_raddr_from_noc <= s.address_upper):
        bank_index_load_from_noc = trunc((recv_raddr_from_noc - s.address_lower) >> per_bank_addr_nbits, XbarOutRdType)
      else:
        bank_index_load_from_noc = XbarOutRdType(num_banks_per_cgra)
      s.rd_pkt[num_rd_tiles] @= MemReadPktType(num_rd_tiles,                                     # src
                                               bank_index_load_from_noc,                         # dst
                                               recv_raddr_from_noc,                              # addr
                                               DataType(0, 0, 0, 0),                             # data
                                               s.recv_from_noc_load_request.msg.src,             # src_cgra
                                               s.recv_from_noc_load_request.msg.src_tile_id,     # src_tile
                                               s.recv_from_noc_load_request.msg.remote_src_port) # remote_src_port

      for i in range(num_wr_tiles):
        recv_waddr = s.recv_waddr[i].msg
        # Calculates the target bank index for store.
        if (recv_waddr >= s.address_lower) & (recv_waddr <= s.address_upper):
          bank_index_store_local = trunc((recv_waddr - s.address_lower) >> per_bank_addr_nbits, XbarOutWrType)
        else:
          bank_index_store_local = XbarOutWrType(num_banks_per_cgra)
        s.wr_pkt[i] @= MemWritePktType(i,                       # src
                                       bank_index_store_local,  # dst
                                       recv_waddr,              # addr
                                       s.recv_wdata[i].msg,     # data
                                       0,                       # src_cgra
                                       0,                       # src_tile
                                       i)                       # remote_src_port

      recv_waddr_from_noc = s.recv_from_noc_store_request.msg.payload.data_addr
      recv_wdata_from_noc = s.recv_from_noc_store_request.msg.payload.data
      if (recv_waddr_from_noc >= s.address_lower) & (recv_waddr_from_noc <= s.address_upper):
        bank_index_store_from_noc = trunc((recv_waddr_from_noc - s.address_lower) >> per_bank_addr_nbits, XbarOutWrType)
      else:
        bank_index_store_from_noc = XbarOutWrType(num_banks_per_cgra)
      s.wr_pkt[num_wr_tiles] @= MemWritePktType(num_wr_tiles,               # src
                                                bank_index_store_from_noc,  # dst
                                                recv_waddr_from_noc,        # addr
                                                recv_wdata_from_noc,        # data
                                                0,                          # src_cgra
                                                0,                          # src_tile
                                                num_wr_tiles)               # remote_src_port

    # Connects xbar with the memory wrapper.
    @update
    def update_all():
      # Initializes the signals.
      for i in range(num_rd_tiles):
        s.recv_raddr[i].rdy @= 0
      s.recv_from_noc_load_request.rdy @= 0

      for i in range(num_wr_tiles):
        s.recv_waddr[i].rdy @= 0
        # s.recv_wdata_bypass_q[i].send.rdy @= 0
      s.recv_from_noc_store_request.rdy @= 0
      # s.recv_wdata_bypass_q[num_wr_tiles].send.rdy @= 0

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
                     0, # remote_src_port
                     0, # opaque
                     0, # vc_id
                     CgraPayloadType(0, 0, 0, 0, 0))


      for i in range(num_wr_tiles):
        s.recv_wdata[i].rdy @= 0

      s.send_to_noc_store_pkt.msg @= \
          NocPktType(0, # src
                     0, # dst
                     0, # src_x
                     0, # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # src_tile_id
                     0, # dst_tile_id
                     0, # remote_src_port
                     0, # opaque
                     0, # vc_id
                     CgraPayloadType(0, 0, 0, 0, 0))

      s.send_to_noc_store_pkt.val @= 0

      for i in range(num_xbar_in_rd_ports):
        s.read_crossbar.recv[i].val @= 0
        s.read_crossbar.recv[i].msg @= MemReadPktType(0, 0, 0, DataType(0, 0, 0, 0), 0, 0, 0)

      s.recv_from_noc_load_response_pkt.rdy @= 0

      for i in range(num_xbar_in_wr_ports):
        s.write_crossbar.recv[i].val @= 0
        s.write_crossbar.recv[i].msg @= MemWritePktType(0, 0, 0, DataType(0, 0, 0, 0), 0, 0, 0)

      s.send_to_noc_load_request_pkt.msg @= \
          NocPktType(0, # src
                     0, # dst
                     0, # src_x
                     0, # src_y
                     0, # dst_x
                     0, # dst_y
                     0, # src_tile_id
                     0, # dst_tile_id
                     0, # remote_src_port
                     0, # opaque
                     0, # vc_id
                     CgraPayloadType(0, 0, 0, 0, 0))

      s.send_to_noc_load_request_pkt.val @= 0

      # Connects the load request ports (from tiles and NoC) to the xbar targetting memory and NoC.
      for i in range(num_rd_tiles):
          s.read_crossbar.recv[i].val @= s.recv_raddr[i].val
          s.read_crossbar.recv[i].msg @= s.rd_pkt[i]
          s.recv_raddr[i].rdy @= s.read_crossbar.recv[i].rdy
      s.read_crossbar.recv[num_rd_tiles].val @= s.recv_from_noc_load_request.val
      s.read_crossbar.recv[num_rd_tiles].msg @= s.rd_pkt[num_rd_tiles]
      s.recv_from_noc_load_request.rdy @= s.read_crossbar.recv[num_rd_tiles].rdy
      
      # Connects the store request ports (from tiles and NoC) to the xbar targetting memory and NoC.
      for i in range(num_wr_tiles):
        s.write_crossbar.recv[i].val @= s.recv_waddr[i].val
        s.write_crossbar.recv[i].msg @= s.wr_pkt[i]
        s.recv_waddr[i].rdy @= s.write_crossbar.recv[i].rdy
        s.recv_wdata[i].rdy @= s.write_crossbar.recv[i].rdy
      s.write_crossbar.recv[num_wr_tiles].val @= s.recv_from_noc_store_request.val
      s.write_crossbar.recv[num_wr_tiles].msg @= s.wr_pkt[num_wr_tiles]
      s.recv_from_noc_store_request.rdy @= s.write_crossbar.recv[num_wr_tiles].rdy

      # Connects the response ports to tiles and NoC from the xbar.
      # Number of load responses is expected to be the same as the number of load requests.
      for i in range(num_xbar_in_rd_ports):
        if i < num_rd_tiles:
          s.send_rdata[RdTileIdType(i)].msg @= s.response_crossbar.send[i].msg.data
          s.send_rdata[RdTileIdType(i)].val @= s.response_crossbar.send[i].val
          s.response_crossbar.send[i].rdy @= s.send_rdata[RdTileIdType(i)].rdy
        else:
          from_cgra_id = s.response_crossbar.send[i].msg.src_cgra
          from_tile_id = s.response_crossbar.send[i].msg.src_tile
          s.send_to_noc_load_response_pkt.msg @= \
                NocPktType(
                    s.cgra_id, # src_cgra_id
                    from_cgra_id, # dst_cgra_id
                    s.idTo2d_x_lut[s.cgra_id], # src_cgra_x
                    s.idTo2d_y_lut[s.cgra_id], # src_cgra_y
                    s.idTo2d_x_lut[from_cgra_id], # dst_cgra_x
                    s.idTo2d_y_lut[from_cgra_id], # dst_cgra_y
                    0, # src_tile_id set as 0 as it is from memory rather than a specific tile.
                    from_tile_id, # dst_tile_id
                    s.response_crossbar.send[i].msg.remote_src_port, # remote_src_port, carries the original source port id towards the src.
                    0, # opaque
                    0, # vc_id
                    CgraPayloadType(
                        CMD_LOAD_RESPONSE,
                        s.response_crossbar.send[i].msg.data,
                        s.response_crossbar.send[i].msg.addr, 0, 0))

          s.send_to_noc_load_response_pkt.val @= s.response_crossbar.send[i].val
          s.response_crossbar.send[i].rdy @= s.send_to_noc_load_response_pkt.rdy

      # Handles the request (not response) towards the others via the NoC. The dst would be
      # updated in the controller.
      s.send_to_noc_load_request_pkt.msg @= \
          NocPktType(s.cgra_id, # src
                      0, # dst
                      s.idTo2d_x_lut[s.cgra_id], # src_x
                      s.idTo2d_y_lut[s.cgra_id], # src_y
                      0, # dst_x
                      0, # dst_y
                      0, # src_tile_id
                      0, # dst_tile_id
                      s.read_crossbar.send[num_banks_per_cgra].msg.src, # remote_src_port
                      0, # opaque
                      0, # vc_id
                      CgraPayloadType(
                          CMD_LOAD_REQUEST,
                          0,
                          s.read_crossbar.send[num_banks_per_cgra].msg.addr, 0, 0))

      s.send_to_noc_load_request_pkt.val @= s.read_crossbar.send[num_banks_per_cgra].val 
      # TODO: https://github.com/tancheng/VectorCGRA/issues/26 -- Modify this part for non-blocking access.
      # 'val` indicates the data is arbitrated successfully.
      s.recv_from_noc_load_response_pkt.rdy @= s.response_crossbar.recv[num_banks_per_cgra].rdy
      s.response_crossbar.recv[num_banks_per_cgra].val @= s.recv_from_noc_load_response_pkt.val
      s.response_crossbar.recv[num_banks_per_cgra].msg @= \
          MemResponsePktType(num_banks_per_cgra,
                             s.recv_from_noc_load_response_pkt.msg.remote_src_port,
                             s.recv_from_noc_load_response_pkt.msg.payload.data_addr,
                             s.recv_from_noc_load_response_pkt.msg.payload.data,
                             s.recv_from_noc_load_response_pkt.msg.src,
                             s.recv_from_noc_load_response_pkt.msg.src_tile_id,
                             0)
      # Allows other load request towards NoC when the previous one is not responded. There
      # could be out-of-order load response, i.e., potential consistency issue.
      s.read_crossbar.send[num_banks_per_cgra].rdy @= s.send_to_noc_load_request_pkt.rdy

      # Handles the write port towards the NoC.
      s.send_to_noc_store_pkt.msg @= \
          NocPktType(s.cgra_id, # src
                      0, # dst
                      s.idTo2d_x_lut[s.cgra_id], # src_x
                      s.idTo2d_y_lut[s.cgra_id], # src_y
                      0, # dst_x
                      0, # dst_y
                      0, # src_tile_id
                      0, # dst_tile_id
                      s.write_crossbar.send[num_banks_per_cgra].msg.src, # remote_src_port
                      0, # opaque
                      0, # vc_id
                      CgraPayloadType(
                          CMD_STORE_REQUEST,
                          s.write_crossbar.send[num_banks_per_cgra].msg.data,
                          s.write_crossbar.send[num_banks_per_cgra].msg.addr, 0, 0))

      s.send_to_noc_store_pkt.val @= s.write_crossbar.send[num_banks_per_cgra].val
      s.write_crossbar.send[num_banks_per_cgra].rdy @= s.send_to_noc_store_pkt.rdy

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
      content_str +=  " bank[" + str(b) + "]: " + "|".join([str(data) for data in s.memory_wrapper[b].memory.regs]) + ";"
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

