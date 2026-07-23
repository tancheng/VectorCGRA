"""
==========================================================================
IntegratedIm2ColWithCgraRTL.py
==========================================================================
Top-level RTL module that integrates an Im2col engine with a CGRA in a
DMA-style topology: the CPU only talks to the CGRA controller, and the
Im2col engine sits behind the controller like a DMA peripheral, with
its own dedicated packet ports on the controller.

The launch flow: a CPU-issued IntraCgraPkt with cmd = CMD_IM2COL_LAUNCH
enters the controller through recv_from_cpu_pkt; the controller
recognizes the cmd and forwards the packet on send_to_im2col_engine_pkt
to trigger engine.start. The engine then reads the preloaded image
from its input scratchpad, computes im2col, and streams the lowered
(kH*kW) x (Hout*Wout) matrix into the CGRA's data memory as a sequence
of CMD_STORE_REQUEST packets that enter the controller through the
engine-dedicated recv_from_im2col_pkt (a separate port so its source is
obvious at the interface level). Both packet streams reach the same
internal crossbar, so they still share downstream routing to data_mem
/ ctrl_ring / NoC.

Architecture:

    +----------------- IntegratedIm2ColWithCgraRTL --------------------+
    |                                                                  |
    |  recv_from_cpu_pkt --------> cgra.recv_from_cpu_pkt              |
    |  (CPU: config / launch /                |                        |
    |   query / CMD_IM2COL_LAUNCH)            |                        |
    |                                         |  send_to_im2col_       |
    |                                         |  engine_pkt (fork of   |
    |                                         |  CMD_IM2COL_LAUNCH)    |
    |                                         v                        |
    |                                  +------+----------+             |
    |                                  |  Im2colEngineRTL |             |
    |                                  |  (Im2col +       |             |
    |                                  |   scratchpads +  |             |
    |                                  |   emit FSM)      |             |
    |                                  +--------+---------+             |
    |                                           | engine.send_pkt       |
    |                                           v                       |
    |                                cgra.recv_from_im2col_pkt          |
    |                                (CMD_STORE_REQUEST preload)        |
    |                                                                   |
    |  CgraRTL (controller dispatches to tiles / data_mem / engine)     |
    |  send_to_cpu_pkt <-- cgra.send_to_cpu_pkt                         |
    |  ... boundary / inter-cgra ports pass through to cgra ...         |
    +-------------------------------------------------------------------+
"""

from pymtl3 import *

from .CgraRTL import CgraRTL
from ..fu.others.Im2colEngineRTL import Im2colEngineRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.messages import (mk_cgra_id_type, mk_inter_cgra_pkt,
                            mk_intra_cgra_pkt)
from ..lib.util.common import KING_MESH, MESH
from ..lib.util.data_struct_attr import (kAttrCtrl, kAttrData, kAttrDataAddr,
                                          kAttrPayload)


class IntegratedIm2ColWithCgraRTL(Component):

  def construct(s, CgraPayloadType,
                multi_cgra_rows, multi_cgra_columns,
                width, height,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank, num_ctrl,
                total_steps, mem_access_is_combinational,
                FunctionUnit, FuList, cgra_topology,
                controller2addr_map, idTo2d_map,
                # Im2col engine parameters (geometry + per-cell routing).
                engine_scratch_mem_size,
                engine_in_base,
                engine_H, engine_W, engine_kH, engine_kW, engine_stride,
                engine_preload_image,
                has_ctrl_ring = True):

    DataType        = CgraPayloadType.get_field_type(kAttrData)
    DataAddrType    = mk_bits(clog2(data_mem_size_global))
    num_tiles       = width * height
    num_rd_tiles    = height + width - 1
    CgraIdType      = mk_cgra_id_type(multi_cgra_columns, multi_cgra_rows)
    CtrlPktType     = mk_intra_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                        num_tiles, CgraPayloadType)
    NocPktType      = mk_inter_cgra_pkt(multi_cgra_columns, multi_cgra_rows,
                                        num_tiles, num_rd_tiles,
                                        CgraPayloadType)

    assert(cgra_topology == MESH or cgra_topology == KING_MESH)

    # External interface. The CPU has exactly one packet input port
    # (recv_from_cpu_pkt) into the CGRA controller; the engine sits
    # behind the controller and receives its trigger from
    # controller.send_to_im2col_engine_pkt. The inter-CGRA NoC ports
    # are not exposed because the integration is single-CGRA by design.
    s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
    s.send_to_cpu_pkt   = SendIfcRTL(CtrlPktType)

    s.recv_data_on_boundary_south = [RecvIfcRTL(DataType) for _ in range(width )]
    s.send_data_on_boundary_south = [SendIfcRTL(DataType) for _ in range(width )]
    s.recv_data_on_boundary_north = [RecvIfcRTL(DataType) for _ in range(width )]
    s.send_data_on_boundary_north = [SendIfcRTL(DataType) for _ in range(width )]
    s.recv_data_on_boundary_east  = [RecvIfcRTL(DataType) for _ in range(height)]
    s.send_data_on_boundary_east  = [SendIfcRTL(DataType) for _ in range(height)]
    s.recv_data_on_boundary_west  = [RecvIfcRTL(DataType) for _ in range(height)]
    s.send_data_on_boundary_west  = [SendIfcRTL(DataType) for _ in range(height)]

    s.cgra_id       = InPort(CgraIdType)
    s.address_lower = InPort(DataAddrType)
    s.address_upper = InPort(DataAddrType)

    # Sub-components.
    s.engine = Im2colEngineRTL(
        DataType, CtrlPktType, CgraPayloadType,
        engine_scratch_mem_size,
        engine_in_base,
        engine_H, engine_W, engine_kH, engine_kW, engine_stride,
        engine_preload_image)

    s.cgra = CgraRTL(CgraPayloadType,
                     multi_cgra_rows, multi_cgra_columns,
                     width, height, ctrl_mem_size,
                     data_mem_size_global, data_mem_size_per_bank,
                     num_banks_per_cgra, num_registers_per_reg_bank,
                     num_ctrl, total_steps, mem_access_is_combinational,
                     FunctionUnit, FuList, cgra_topology,
                     controller2addr_map, idTo2d_map,
                     is_multi_cgra = False,
                     has_ctrl_ring = has_ctrl_ring,
                     has_im2col_engine = True)

    # DMA-style trigger. The CGRA controller forks packets whose
    # payload.cmd == CMD_IM2COL_LAUNCH to send_to_im2col_engine_pkt;
    # we drive engine.start with the val of that stream (one-cycle
    # pulse) and always acknowledge with rdy=1.
    s.engine.start                       //= s.cgra.send_to_im2col_engine_pkt.val
    s.cgra.send_to_im2col_engine_pkt.rdy //= 1

    # Pass-through wiring to CgraRTL.
    s.cgra.cgra_id       //= s.cgra_id
    s.cgra.address_lower //= s.address_lower
    s.cgra.address_upper //= s.address_upper

    s.send_to_cpu_pkt //= s.cgra.send_to_cpu_pkt

    # Tie off the inner CGRA's unused inter-CGRA NoC ports. With
    # is_multi_cgra=False the inner CGRA bypasses inter-CGRA traffic
    # internally but still exposes these top-level ports; we drive
    # them to a quiescent state so elaboration sees a writer.
    s.cgra.recv_from_inter_cgra_noc.val //= 0
    s.cgra.recv_from_inter_cgra_noc.msg //= NocPktType()
    s.cgra.send_to_inter_cgra_noc.rdy   //= 0

    for i in range(width):
      s.recv_data_on_boundary_south[i] //= s.cgra.recv_data_on_boundary_south[i]
      s.send_data_on_boundary_south[i] //= s.cgra.send_data_on_boundary_south[i]
      s.recv_data_on_boundary_north[i] //= s.cgra.recv_data_on_boundary_north[i]
      s.send_data_on_boundary_north[i] //= s.cgra.send_data_on_boundary_north[i]

    for i in range(height):
      s.recv_data_on_boundary_east[i] //= s.cgra.recv_data_on_boundary_east[i]
      s.send_data_on_boundary_east[i] //= s.cgra.send_data_on_boundary_east[i]
      s.recv_data_on_boundary_west[i] //= s.cgra.recv_data_on_boundary_west[i]
      s.send_data_on_boundary_west[i] //= s.cgra.send_data_on_boundary_west[i]

    # Direct point-to-point wiring for the two producer streams. The
    # CPU and the engine each drive their own dedicated port into the
    # CGRA controller, so the source of every packet is honest at the
    # interface.
    #
    # However, we still gate the CPU stream while a preload is in
    # flight: the CPU packet list contains the systolic config/launch
    # packets for every tile immediately after the CMD_IM2COL_LAUNCH,
    # and without this gate the tile launches would race the engine's
    # store requests and execute against un-preloaded SRAM.
    #
    # `engine_active` rises on engine.start (the cycle we fork
    # CMD_IM2COL_LAUNCH to the engine) and clears on engine.done. While
    # high, the CPU-facing recv_from_cpu_pkt is held (rdy=0) so
    # subsequent CPU packets wait. The engine's dedicated
    # recv_from_im2col_pkt is unaffected -- it carries the preload
    # stream freely.
    s.engine.send_pkt //= s.cgra.recv_from_im2col_pkt

    s.engine_active = Wire(b1)

    @update_ff
    def update_engine_active():
      if s.reset:
        s.engine_active <<= b1(0)
      else:
        if s.engine.start:
          s.engine_active <<= b1(1)
        elif s.engine.done:
          s.engine_active <<= b1(0)

    @update
    def gate_cpu_stream():
      if s.engine_active:
        s.cgra.recv_from_cpu_pkt.val @= b1(0)
        s.cgra.recv_from_cpu_pkt.msg @= s.recv_from_cpu_pkt.msg
        s.recv_from_cpu_pkt.rdy      @= b1(0)
      else:
        s.cgra.recv_from_cpu_pkt.val @= s.recv_from_cpu_pkt.val
        s.cgra.recv_from_cpu_pkt.msg @= s.recv_from_cpu_pkt.msg
        s.recv_from_cpu_pkt.rdy      @= s.cgra.recv_from_cpu_pkt.rdy

  def line_trace(s):
    return s.engine.line_trace() + ' || ' + s.cgra.line_trace()
