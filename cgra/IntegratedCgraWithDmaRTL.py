"""
=========================================================================
IntegratedCgraWithDmaRTL.py
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


class IntegratedCgraWithDmaRTL( Component ):
  """
  IntegratedCgraWithDmaRTL is a top-level wrapper that integrates a CGRA instance with a
  DMA engine.

  Architectural Design:
  - It instantiates a standard CGRA template (`CgraTemplateRTL`) and a
    DMA engine (`DmaEngineRTL`).
  - CPU control packets are passed through to the CGRA's controller.
    DMA commands are decoded there.
  - The DMA engine accesses the CGRA's internal data SPM through controller-
    forwarded ports; it is not connected directly to `DataMemControllerRTL`.
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
                # For heterogeneous multi-cgra support.(maybe remove it in IntegratedCgraWithDmaRTL for simplicity?)
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
    DmaCmdType = mk_dma_cmd(dram_addr_nbits = 64,
                            spm_addr_nbits = 32,
                            bytes_nbits = 32,
                            tag_nbits = 8)

    DmaDataType = mk_dma_data(dram_data_nbits = 128,
                              dram_mask_nbits = 16,
                              spm_data_nbits = 32)

    DmaDramAddrType = DmaCmdType.get_field_type(kAttrDramAddr)
    DmaMemDataType  = DmaDataType.get_field_type(kAttrDramData)
    DmaMemMaskType  = DmaDataType.get_field_type(kAttrDramMask)
    DmaDramWrReqType = mk_dma_dram_wr_req(DmaDramAddrType.nbits, DmaMemDataType.nbits, DmaMemMaskType.nbits)

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

    # Abstract external dram memory interfaces for the internal DMA engine.

    s.send_to_dram_rd_req = SendIfcRTL(DmaDramAddrType)
    s.recv_from_dram_rd_resp = RecvIfcRTL(DmaMemDataType)

    s.send_to_dram_wr_req = SendIfcRTL(DmaDramWrReqType)
    s.recv_from_dram_wr_resp = RecvIfcRTL(mk_bits(1))

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
                             has_dma_ports = True,
                             DmaDataType = DmaDataType,
                             DmaCmdType = DmaCmdType)

    DmaSpmDataType = DmaDataType.get_field_type(kAttrSpmData)
    DmaSpmAddrType = DmaCmdType.get_field_type(kAttrSpmAddr)
    DmaBytesType = DmaCmdType.get_field_type(kAttrNBytes)
    DmaTagType = DmaCmdType.get_field_type(kAttrTag)
    s.dma = DmaEngineRTL(spm_data_nbits = DmaSpmDataType.nbits,
                         dram_data_nbits = DmaMemDataType.nbits,
                         dram_addr_nbits = DmaDramAddrType.nbits,
                         spm_addr_nbits = DmaSpmAddrType.nbits,
                         bytes_nbits = DmaBytesType.nbits,
                         tag_nbits = DmaTagType.nbits)

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


    # Connections between CGRA and DMA engine.
    # CGRA communicates with DMA engine through the controller.
    s.cgra.dma_cmd  //= s.dma.dma_cmd
    s.dma.dma_done  //= s.cgra.dma_done

    s.send_to_dram_rd_req  //= s.dma.send_to_dram_rd_req
    s.recv_from_dram_rd_resp //= s.dma.recv_from_dram_rd_resp

    s.send_to_dram_wr_req       //= s.dma.send_to_dram_wr_req
    s.recv_from_dram_wr_resp      //= s.dma.recv_from_dram_wr_resp

    # DMA to controller-forwarded SPM connections.

    s.dma.send_to_spm_wr_req //= s.cgra.recv_from_dma_spm_wr_req
    s.dma.send_to_spm_rd_req  //= s.cgra.recv_from_dma_spm_rd_req
    s.dma.recv_from_spm_rd_resp //= s.cgra.send_to_dma_spm_rd_resp

  def line_trace(s):
    return f"{s.dma.line_trace()} || {s.cgra.line_trace()}"
