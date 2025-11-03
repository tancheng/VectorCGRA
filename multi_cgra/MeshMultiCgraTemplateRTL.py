from ..cgra.CgraRTL import CgraRTL
from ..cgra.CgraTemplateRTL import CgraTemplateRTL
from ..lib.basic.val_rdy.ifcs import ValRdyRecvIfcRTL as RecvIfcRTL
from ..lib.basic.val_rdy.ifcs import ValRdySendIfcRTL as SendIfcRTL
from ..lib.opt_type import *
from ..noc.PyOCN.pymtl3_net.meshnet.MeshNetworkRTL import MeshNetworkRTL
from ..noc.PyOCN.pymtl3_net.ocnlib.ifcs.positions import mk_mesh_pos

class MeshMultiCgraTemplateRTL(Component):

    def construct(s, CgraDataType, PredicateType, CtrlPktType,
                CgraPayloadType, CtrlSignalType, NocPktType, data_nbits,
                cgra_rows, cgra_columns, 
                # per_cgra_rows, per_cgra_columns,
                ctrl_mem_size, data_mem_size_global,
                data_mem_size_per_bank, num_banks_per_cgra,
                num_registers_per_reg_bank,
                num_ctrl, total_steps, FunctionUnit, FuList,
                controller2addr_map, id2ctrlMemSize_map, id2cgraSize_map, 
                id2validTiles, id2validLinks, id2dataSPM,
                mem_access_is_combinational,
                is_multi_cgra = True):

        # Constant
        s.num_cgras = cgra_rows * cgra_columns
        idTo2d_map = {}

        # Mesh position takes column as argument first.
        MeshPos = mk_mesh_pos(cgra_columns, cgra_rows)
        # s.num_tiles = per_cgra_rows * per_cgra_columns
        # CtrlAddrType = mk_bits(clog2(ctrl_mem_size))
        DataAddrType = mk_bits(clog2(data_mem_size_global))
        ControllerIdType = mk_bits(max(1, clog2(s.num_cgras)))

        # Interface
        # Request from/to CPU.
        s.recv_from_cpu_pkt = RecvIfcRTL(CtrlPktType)
        s.send_to_cpu_pkt = SendIfcRTL(CtrlPktType)

        # Components
        for cgra_row in range(cgra_rows):
          for cgra_col in range(cgra_columns):
            idTo2d_map[cgra_row * cgra_columns + cgra_col] = (cgra_col, cgra_row)

        s.cgra = [CgraTemplateRTL(CgraPayloadType,
                                  cgra_rows, cgra_columns, 
                                  # per_cgra_rows, per_cgra_columns,
                                  id2cgraSize_map[cgra_id][0], id2cgraSize_map[cgra_id][1],    
                                  # ctrl_mem_size, 
                                  id2ctrlMemSize_map[cgra_id],
                                  data_mem_size_global,
                                  data_mem_size_per_bank, 
                                  num_banks_per_cgra,
                                  num_registers_per_reg_bank,
                                  num_ctrl, total_steps,
                                  mem_access_is_combinational,
                                  FunctionUnit, FuList,
                                  id2validTiles[cgra_id], id2validLinks[cgra_id], id2dataSPM[cgra_id],
                                  controller2addr_map, idTo2d_map,
                                  is_multi_cgra
                                  )
                  for cgra_id in range(s.num_cgras)]
        # class CgraTemplateRTL(Component):
        #     def construct(s, DataType, PredicateType, CtrlPktType, CgraPayloadType,
        #         CtrlSignalType, NocPktType, CgraIdType, multi_cgra_rows,
        #         multi_cgra_columns, ctrl_mem_size, data_mem_size_global,
        #         data_mem_size_per_bank, num_banks_per_cgra,
        #         num_registers_per_reg_bank, num_ctrl, 
        #         total_steps, FunctionUnit, FuList, TileList, LinkList,
        #         dataSPM, controller2addr_map, idTo2d_map,
        #         preload_data = None,
        #         is_multi_cgra = True,
        #         cgraWidth = 2,
        #         cgraHeight = 2):



        # s.cgra = [CgraRTL(CgraDataType, PredicateType, CtrlPktType,
        #               CgraPayloadType, CtrlSignalType, NocPktType,
        #               ControllerIdType, cgra_rows, cgra_columns,
        #               per_cgra_columns, per_cgra_rows,
        #               ctrl_mem_size, data_mem_size_global,
        #               data_mem_size_per_bank, num_banks_per_cgra,
        #               num_registers_per_reg_bank,
        #               num_ctrl, total_steps, FunctionUnit, FuList,
        #               "Mesh", controller2addr_map, idTo2d_map,
        #               preload_data = None)
        #       for cgra_id in range(s.num_cgras)]
        # Latency is 1.
        s.mesh = MeshNetworkRTL(NocPktType, MeshPos, cgra_columns, cgra_rows, 1)

        # Connections
        for i in range(s.num_cgras):
          s.mesh.send[i] //= s.cgra[i].recv_from_inter_cgra_noc
          s.mesh.recv[i] //= s.cgra[i].send_to_inter_cgra_noc

        # Connects controller id.
        for cgra_id in range(s.num_cgras):
          s.cgra[cgra_id].cgra_id //= cgra_id

        # Connects memory address upper and lower bound for each CGRA.
        for cgra_id in range(s.num_cgras):
          s.cgra[cgra_id].address_lower //= DataAddrType(controller2addr_map[cgra_id][0])
          s.cgra[cgra_id].address_upper //= DataAddrType(controller2addr_map[cgra_id][1])

        s.recv_from_cpu_pkt //= s.cgra[0].recv_from_cpu_pkt
        s.send_to_cpu_pkt //= s.cgra[0].send_to_cpu_pkt

        for i in range(1, s.num_cgras):
          s.cgra[i].recv_from_cpu_pkt.val //= 0
          s.cgra[i].recv_from_cpu_pkt.msg //= CtrlPktType()
          s.cgra[i].send_to_cpu_pkt.rdy //= 0

        # Connects the tiles on the boundary of each two adjacent CGRAs.
        # Example for 4 CGRAs (2x2):
        #              (cgra_col=0)   -- (cgra_col=1)
        # (cgra_row=1) CGRA 2 [idx=2] -- CGRA 3 [idx=3]
        # (cgra_row=0) CGRA 0 [idx=0] -- CGRA 1 [idx=1]
        for cgra_row in range(cgra_rows):
          for cgra_col in range(cgra_columns):
            idx = cgra_row * cgra_columns + cgra_col
            per_cgra_rows = id2cgraSize_map[idx][0]
            per_cgra_columns = id2cgraSize_map[idx][1]
            
            # Connects North-South boundaries
            if cgra_row > 0:
              neighbor_idx = (cgra_row - 1) * cgra_columns + cgra_col
              for tile_col in range(per_cgra_columns):
                s.cgra[idx].send_data_on_boundary_south[tile_col] //= \
                    s.cgra[neighbor_idx].recv_data_on_boundary_north[tile_col]
                s.cgra[idx].recv_data_on_boundary_south[tile_col] //= \
                    s.cgra[neighbor_idx].send_data_on_boundary_north[tile_col]
            else:
              # Bottom edge: connects south boundary to 0
              for tile_col in range(per_cgra_columns):
                s.cgra[idx].recv_data_on_boundary_south[tile_col].val //= 0
                s.cgra[idx].recv_data_on_boundary_south[tile_col].msg //= CgraDataType()
                s.cgra[idx].send_data_on_boundary_south[tile_col].rdy //= 0

            # Top edge: connects north boundary to 0
            if cgra_row == cgra_rows - 1:
              for tile_col in range(per_cgra_columns):
                s.cgra[idx].recv_data_on_boundary_north[tile_col].val //= 0
                s.cgra[idx].recv_data_on_boundary_north[tile_col].msg //= CgraDataType()
                s.cgra[idx].send_data_on_boundary_north[tile_col].rdy //= 0

            # Connect East-West boundaries
            if cgra_col > 0:
              neighbor_idx = cgra_row * cgra_columns + cgra_col - 1
              for tile_row in range(per_cgra_rows):
                s.cgra[idx].send_data_on_boundary_west[tile_row] //= \
                    s.cgra[neighbor_idx].recv_data_on_boundary_east[tile_row]
                s.cgra[idx].recv_data_on_boundary_west[tile_row] //= \
                    s.cgra[neighbor_idx].send_data_on_boundary_east[tile_row]
            else:
              # Left edge: connects west boundary to 0
              for tile_row in range(per_cgra_rows):
                s.cgra[idx].recv_data_on_boundary_west[tile_row].val //= 0
                s.cgra[idx].recv_data_on_boundary_west[tile_row].msg //= CgraDataType()
                s.cgra[idx].send_data_on_boundary_west[tile_row].rdy //= 0
                
            # Right edge: connects east boundary to 0
            if cgra_col == cgra_columns - 1:
              for tile_row in range(per_cgra_rows):
                s.cgra[idx].recv_data_on_boundary_east[tile_row].val //= 0
                s.cgra[idx].recv_data_on_boundary_east[tile_row].msg //= CgraDataType()
                s.cgra[idx].send_data_on_boundary_east[tile_row].rdy //= 0

    def line_trace(s):
        res = "||\n".join([(("\n\n[cgra_"+str(i)+": ") + x.line_trace())
                        for (i,x) in enumerate(s.cgra)])
        res += " ## mesh: " + s.mesh.line_trace()
        return res