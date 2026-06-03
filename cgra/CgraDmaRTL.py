"""
=========================================================================
CgraDmaRTL.py
=========================================================================

Wrapper that composes a CGRA template with a DMA engine attached to the
CGRA data SPM.
"""

from pymtl3 import *

from .CgraTemplateRTL import CgraTemplateRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.messages import *
from ..lib.util.data_struct_attr import *
from ..mem.dma.DmaEngineRTL import DmaEngineRTL


class CgraDmaRTL( Component ):
  """
  CgraDmaRTL is a top-level wrapper that integrates a CGRA instance with a
  DMA engine.

  Architectural Design:
  - It instantiates a standard CGRA template (`CgraTemplateRTL`) and a
    DMA engine (`DmaEngineRTL`).
  - The DMA engine is connected to the CGRA's internal data SPM through a
    dedicated master port on the `DataMemControllerRTL`.
  - CPU control packets are passed through to the CGRA's controller.
  - External memory requests from the DMA engine are exposed at the top level
    to be connected to a DRAM model or an AXI adapter.
  - Boundary data ports for multi-CGRA configurations are also passed through
    if enabled.
  """

  def construct(s, CgraPayloadType,
                multi_cgra_rows,
                multi_cgra_columns,
                per_cgra_rows, per_cgra_columns,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, mem_access_is_combinational,
                FunctionUnit, FuList, TileList, LinkList,
                dataSPM, controller2addr_map, idTo2d_map,
                is_multi_cgra = True, cgra_id = 0,
                # For heterogeneous multi-cgra support.(maybe remove it in CgraDmaRTL for simplicity?)
                provided_max_per_cgra_rows = None,
                provided_max_per_cgra_cols = None,
                provided_max_num_rd_tiles = None,
                provided_max_num_wr_tiles = None):

    DataType = CgraPayloadType.get_field_type(kAttrData)
    data_bitwidth = DataType.get_field_type(kAttrPayload).nbits
    assert data_bitwidth == 32

    max_per_cgra_rows = provided_max_per_cgra_rows if provided_max_per_cgra_rows is not None else per_cgra_rows
    max_per_cgra_cols = provided_max_per_cgra_cols if provided_max_per_cgra_cols is not None else per_cgra_columns
    max_num_tiles = max_per_cgra_rows * max_per_cgra_cols
    max_num_rd_tiles = provided_max_num_rd_tiles if provided_max_num_rd_tiles is not None else dataSPM.getNumOfValidReadPorts()

    CtrlPktType = mk_intra_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                    max_num_tiles, CgraPayloadType)
    NocPktType = mk_inter_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                   max_num_tiles, max_num_rd_tiles,
                                   CgraPayloadType)

    CgraIdType = mk_cgra_id_type(multi_cgra_columns, multi_cgra_rows)
    DataAddrType = mk_bits(clog2(data_mem_size_global))
    DmaOpcodeType = mk_bits(3) #DMA_MVIN: 0, DMA_MVOUT: 1
    DmaDramAddrType = mk_bits(64)
    DmaBytesType = mk_bits(32)
    DmaTagType = mk_bits(8)
    DmaMemDataType = mk_bits(128) # Write/Read 128 bits data per beat from/to DRAM
    DmaMemMaskType = mk_bits(16)

    # Existing CGRA-facing interfaces.
    # CGRA <-> CPU
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)

    if is_multi_cgra:
      s.recv_from_inter_cgra_noc = RecvIfcRTL(NocPktType)
      s.send_to_inter_cgra_noc = SendIfcRTL(NocPktType)

      s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(max_per_cgra_cols)]
      s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_rows)]
      s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(max_per_cgra_rows)]
      s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(max_per_cgra_rows)]
      s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(max_per_cgra_rows)]

    s.cgra_id = InPort(CgraIdType)
    # The local address range of current CGRA.
    # Any address out of this range will be assumed as remote address.
    s.address_lower = InPort(DataAddrType)
    s.address_upper = InPort(DataAddrType)

    # DMA command/done and abstract external memory interfaces.

    s.dma_cmd_val       = InPort() # dma_command_valid
    s.dma_cmd_rdy       = OutPort() # dma_command_ready
    s.dma_cmd_opcode    = InPort(DmaOpcodeType)
    s.dma_cmd_dram_addr = InPort(DmaDramAddrType)
    s.dma_cmd_spm_addr  = InPort(DataAddrType)
    s.dma_cmd_bytes     = InPort(DmaBytesType) # The number of bytes to transfer.
    s.dma_cmd_tag       = InPort(DmaTagType) # Doesn't use it now, but keep it for future use(e.g., distinguish different DMA commands).

    s.dma_done_val      = OutPort()
    s.dma_done_rdy      = InPort()
    s.dma_done_tag      = OutPort(DmaTagType) # Must be same as the input `dma_cmd_tag`

    s.dram_rd_req = SendIfcRTL(DmaDramAddrType)
    s.dram_rd_resp = RecvIfcRTL(DmaMemDataType)

    s.dram_wr_req_val    = OutPort()
    s.dram_wr_req_rdy    = InPort()
    s.dram_wr_req_addr   = OutPort(DmaDramAddrType)
    s.dram_wr_req_data   = OutPort(DmaMemDataType)
    s.dram_wr_req_mask   = OutPort(DmaMemMaskType) # Masks for wrting DRAM

    s.dram_wr_resp_val   = InPort()
    s.dram_wr_resp_rdy   = OutPort()

    # Components.

    s.cgra = CgraTemplateRTL(CgraPayloadType,
                             multi_cgra_rows,
                             multi_cgra_columns,
                             per_cgra_rows, per_cgra_columns,
                             ctrl_mem_size, data_mem_size_global,
                             data_mem_size_per_bank, num_banks_per_cgra,
                             num_registers_per_reg_bank, num_ctrl,
                             total_steps, mem_access_is_combinational,
                             FunctionUnit, FuList, TileList, LinkList,
                             dataSPM, controller2addr_map, idTo2d_map,
                             is_multi_cgra, cgra_id,
                             provided_max_per_cgra_rows,
                             provided_max_per_cgra_cols,
                             provided_max_num_rd_tiles,
                             provided_max_num_wr_tiles,
                             has_dma_ports = True)

    s.dma = DmaEngineRTL(spm_data_nbits = data_bitwidth,
                         spm_addr_nbits = clog2(data_mem_size_global))

    # CGRA passthrough connections.

    s.recv_from_cpu_pkt //= s.cgra.recv_from_cpu_pkt
    s.send_to_cpu_pkt //= s.cgra.send_to_cpu_pkt

    if is_multi_cgra:
      s.recv_from_inter_cgra_noc //= s.cgra.recv_from_inter_cgra_noc
      s.send_to_inter_cgra_noc //= s.cgra.send_to_inter_cgra_noc

      for i in range(max_per_cgra_cols):
        s.recv_data_on_boundary_north[i] //= s.cgra.recv_data_on_boundary_north[i]
        s.send_data_on_boundary_north[i] //= s.cgra.send_data_on_boundary_north[i]
        s.recv_data_on_boundary_south[i] //= s.cgra.recv_data_on_boundary_south[i]
        s.send_data_on_boundary_south[i] //= s.cgra.send_data_on_boundary_south[i]

      for i in range(max_per_cgra_rows):
        s.recv_data_on_boundary_west[i] //= s.cgra.recv_data_on_boundary_west[i]
        s.send_data_on_boundary_west[i] //= s.cgra.send_data_on_boundary_west[i]
        s.recv_data_on_boundary_east[i] //= s.cgra.recv_data_on_boundary_east[i]
        s.send_data_on_boundary_east[i] //= s.cgra.send_data_on_boundary_east[i]

    s.cgra_id //= s.cgra.cgra_id
    s.address_lower //= s.cgra.address_lower
    s.address_upper //= s.cgra.address_upper

    # DMA top-level connections.

    s.dma_cmd_val       //= s.dma.dma_cmd_val
    s.dma_cmd_rdy       //= s.dma.dma_cmd_rdy
    s.dma_cmd_opcode    //= s.dma.dma_cmd_opcode
    s.dma_cmd_dram_addr //= s.dma.dma_cmd_dram_addr
    s.dma_cmd_spm_addr  //= s.dma.dma_cmd_spm_addr
    s.dma_cmd_bytes     //= s.dma.dma_cmd_bytes
    s.dma_cmd_tag       //= s.dma.dma_cmd_tag

    s.dma_done_val      //= s.dma.dma_done_val
    s.dma_done_rdy      //= s.dma.dma_done_rdy
    s.dma_done_tag      //= s.dma.dma_done_tag

    s.dram_rd_req       //= s.dma.dram_rd_req
    s.dram_rd_resp      //= s.dma.dram_rd_resp

    s.dram_wr_req_val    //= s.dma.dram_wr_req_val
    s.dram_wr_req_rdy    //= s.dma.dram_wr_req_rdy
    s.dram_wr_req_addr   //= s.dma.dram_wr_req_addr
    s.dram_wr_req_data   //= s.dma.dram_wr_req_data
    s.dram_wr_req_mask   //= s.dma.dram_wr_req_mask

    s.dram_wr_resp_val   //= s.dma.dram_wr_resp_val
    s.dram_wr_resp_rdy   //= s.dma.dram_wr_resp_rdy

    # DMA to SPM connections.

    s.dma.spm_dma_wval       //= s.cgra.spm_dma_wval
    s.dma.spm_dma_wrdy       //= s.cgra.spm_dma_wrdy
    s.dma.spm_dma_waddr      //= s.cgra.spm_dma_waddr
    s.dma.spm_dma_wdata      //= s.cgra.spm_dma_wdata
    s.dma.spm_dma_wmask      //= s.cgra.spm_dma_wmask

    s.dma.spm_dma_rval       //= s.cgra.spm_dma_rval
    s.dma.spm_dma_rrdy       //= s.cgra.spm_dma_rrdy
    s.dma.spm_dma_raddr      //= s.cgra.spm_dma_raddr
    s.dma.spm_dma_rresp_val  //= s.cgra.spm_dma_rresp_val
    s.dma.spm_dma_rresp_rdy  //= s.cgra.spm_dma_rresp_rdy
    s.dma.spm_dma_rresp_data //= s.cgra.spm_dma_rresp_data

  def line_trace(s):
    return f"{s.dma.line_trace()} || {s.cgra.line_trace()}"
