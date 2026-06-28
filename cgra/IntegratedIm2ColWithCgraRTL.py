"""
==========================================================================
IntegratedIm2ColWithCgraRTL.py
==========================================================================
Top-level RTL module that integrates an Im2col engine with a CGRA.

The Im2colEngineRTL produces a stream of CMD_STORE_REQUEST packets that
preload activations into the CGRA's data memory; this stream is
arbitrated together with the external `recv_from_cpu_pkt` stream into
the single packet input of the CGRA controller. The engine wins until
it asserts `done`, then the external stream takes over.

Architecture:

    +----------------- IntegratedIm2ColWithCgraRTL -----------------+
    |                                                                |
    |  start_im2col                                                  |
    |       |                                                        |
    |       v                                                        |
    |  +--------------------+                                        |
    |  |   Im2colEngineRTL  |  engine.send_pkt                       |
    |  | (Im2col +          | --------------+                        |
    |  |  scratchpads +     |               |                        |
    |  |  emit FSM)         |               v                        |
    |  +--------------------+         +-----------+                  |
    |       |                         | preload   | --> cgra         |
    |       v                         | arbiter   |     .recv_from_  |
    |  im2col_done                    +-----------+     cpu_pkt      |
    |                                       ^                        |
    |  recv_from_cpu_pkt ------------------'                         |
    |  (residual systolic                                            |
    |   config + query pkts)                                         |
    |                                                                |
    |  CgraRTL (controller, ctrl_ring, data_mem, tile[0..n-1], NoC)  |
    |                                                                |
    |  send_to_cpu_pkt <-- cgra.send_to_cpu_pkt                      |
    |  ... boundary / inter-cgra ports pass through to cgra ...      |
    +----------------------------------------------------------------+
"""

from pymtl3 import *

from .CgraRTL import CgraRTL
from .Im2colEngineRTL import Im2colEngineRTL
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
                engine_in_base, engine_out_base,
                engine_H, engine_W, engine_kH, engine_kW, engine_stride,
                engine_dst_tiles, engine_data_addrs, engine_preload_image,
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

    # External interface (mirrors CgraRTL plus start/done; the inter-CGRA
    # NoC ports are not exposed because the integration is single-CGRA by
    # design, and the inner CGRA is instantiated with is_multi_cgra=False
    # so it bypasses inter-CGRA traffic internally).
    s.start_im2col = InPort(b1)
    s.im2col_done  = OutPort(b1)

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
        engine_in_base, engine_out_base,
        engine_H, engine_W, engine_kH, engine_kW, engine_stride,
        engine_dst_tiles, engine_data_addrs, engine_preload_image)

    s.cgra = CgraRTL(CgraPayloadType,
                     multi_cgra_rows, multi_cgra_columns,
                     width, height, ctrl_mem_size,
                     data_mem_size_global, data_mem_size_per_bank,
                     num_banks_per_cgra, num_registers_per_reg_bank,
                     num_ctrl, total_steps, mem_access_is_combinational,
                     FunctionUnit, FuList, cgra_topology,
                     controller2addr_map, idTo2d_map,
                     is_multi_cgra = False,
                     has_ctrl_ring = has_ctrl_ring)

    # Wire engine control.
    s.engine.start //= s.start_im2col
    s.im2col_done  //= s.engine.done

    # Pass-through wiring to CgraRTL.
    s.cgra.cgra_id       //= s.cgra_id
    s.cgra.address_lower //= s.address_lower
    s.cgra.address_upper //= s.address_upper

    s.send_to_cpu_pkt //= s.cgra.send_to_cpu_pkt

    # Tie off the inner CGRA's unused inter-CGRA NoC ports. With
    # is_multi_cgra=False the inner CGRA bypasses inter-CGRA traffic
    # internally but still exposes these top-level ports; we drive
    # them to a quiescent state so elaboration sees a writer. We use
    # construct-level //= rather than an @update block so the verilator
    # translator sees a constant net (the NoC payload contains nested
    # list-of-bits fields that the behavioral translator can't encode).
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

    # Preload-packet arbiter into the controller-facing recv_from_cpu_pkt.
    # The engine has priority until it asserts done; afterwards the
    # external CPU packet stream owns the port. We drive cgra.*.msg from a
    # real signal in BOTH branches (rather than zero-defaulting at the
    # top with CtrlPktType()) because the verilator translator can't
    # encode nested-bitstruct default constructors in behavioral RTLIR.
    @update
    def preload_pkt_arbiter():
      s.engine.send_pkt.rdy   @= b1(0)
      s.recv_from_cpu_pkt.rdy @= b1(0)

      if ~s.engine.done:
        s.cgra.recv_from_cpu_pkt.val @= s.engine.send_pkt.val
        s.cgra.recv_from_cpu_pkt.msg @= s.engine.send_pkt.msg
        s.engine.send_pkt.rdy        @= s.cgra.recv_from_cpu_pkt.rdy
      else:
        s.cgra.recv_from_cpu_pkt.val @= s.recv_from_cpu_pkt.val
        s.cgra.recv_from_cpu_pkt.msg @= s.recv_from_cpu_pkt.msg
        s.recv_from_cpu_pkt.rdy      @= s.cgra.recv_from_cpu_pkt.rdy

  def line_trace(s):
    return s.engine.line_trace() + ' || ' + s.cgra.line_trace()
