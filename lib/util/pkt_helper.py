

import json
from pymtl3 import *
from enum import Enum
from collections import defaultdict

from .common import *
from ..messages import *
from ..opt_type import *

class TilePortEnum(Enum):
    N = PORT_NORTH
    S = PORT_SOUTH
    W = PORT_WEST
    E = PORT_EAST
    NW = PORT_NORTHWEST
    NE = PORT_NORTHEAST
    SE = PORT_SOUTHEAST
    SW = PORT_SOUTHWEST


def _mapped_wr_tokenizer_idx(wr_port_idx):
    if wr_port_idx < 4:
        return ((wr_port_idx & 0x1) << 1) + ((wr_port_idx & 0x2) >> 1)
    return wr_port_idx


def _get_thread_range(metadata, overflow_thread_cap=None):
    max_thread_idx = MAX_THREAD_COUNT - 1
    thread_count_min = int(metadata.get('thread_count_min', 0))
    thread_count_max = int(metadata.get('thread_count_max', thread_count_min))
    if 'thread_count' in metadata:
        thread_count_max = max(thread_count_max, thread_count_min + int(metadata['thread_count']))
    if (thread_count_max > max_thread_idx) and (overflow_thread_cap is not None):
        thread_count_max = min(thread_count_max, thread_count_min + int(overflow_thread_cap))
    thread_count_min = max(0, min(thread_count_min, max_thread_idx))
    thread_count_max = max(thread_count_min, min(thread_count_max, max_thread_idx))
    thread_span = max(0, thread_count_max - thread_count_min)
    return thread_span, thread_count_min, thread_count_max


def _iter_cfg_entries(data):
    cfg_items = [
        (key, value) for key, value in data.items()
        if key.startswith('cfg_')
    ]
    return sorted(cfg_items, key=lambda item: item[1]['metadata']['cfg_id'])


def _default_tile_fwd_route(num_tile_inports, num_tile_outports):
    return [[0 for _ in range(num_tile_outports)] for _ in range(num_tile_inports)]


def _resolve_opt_type(opt_name):
    opt_aliases = {
        'OPT_EXT': 'OPT_PAS',
        'OPT_TRUNC': 'OPT_PAS',
    }
    resolved_name = opt_aliases.get(opt_name, opt_name)
    return globals()[resolved_name]


def _augment_tokenizer_routes(metadata, num_rd_ports, num_wr_ports, num_ld_ports, num_st_ports):
    route_lists = [
        list(route) for route in metadata['tokenizer']['token_route_sink_enable']
    ]

    pred_enabled = metadata.get('in_pred_en', [0] * num_rd_ports)
    enabled_inputs = [
        idx for idx in range(num_rd_ports)
        if metadata['in_regs_val'][idx] or pred_enabled[idx]
    ]
    if not enabled_inputs:
        return route_lists

    trigger_input_idx = enabled_inputs[-1]
    for candidate_idx in reversed(enabled_inputs):
        if any(route_lists[candidate_idx]):
            trigger_input_idx = candidate_idx
            break

    for wr_port_idx in range(num_wr_ports):
        write_enabled = metadata['out_regs_val'][wr_port_idx] or metadata.get(
            'out_pred_regs_val',
            [0] * num_wr_ports,
        )[wr_port_idx]
        if not write_enabled:
            continue

        tokenizer_wr_idx = _mapped_wr_tokenizer_idx(wr_port_idx)
        has_mapped_route = any(route[tokenizer_wr_idx] for route in route_lists)
        has_logical_route = any(route[wr_port_idx] for route in route_lists)
        if has_mapped_route or has_logical_route:
            continue

        route_lists[trigger_input_idx][tokenizer_wr_idx] = 1
        route_lists[trigger_input_idx][wr_port_idx] = 1

    for ld_port_idx in range(num_ld_ports):
        if not metadata['ld_enable'][ld_port_idx]:
            continue
        tokenizer_ld_idx = num_wr_ports + ld_port_idx
        if any(route[tokenizer_ld_idx] for route in route_lists):
            continue
        route_lists[trigger_input_idx][tokenizer_ld_idx] = 1

    for st_port_idx in range(num_st_ports):
        if not metadata['st_enable'][st_port_idx]:
            continue
        tokenizer_st_idx = num_wr_ports + num_ld_ports + st_port_idx
        if any(route[tokenizer_st_idx] for route in route_lists):
            continue
        route_lists[trigger_input_idx][tokenizer_st_idx] = 1

    return route_lists

def generateCPUPktFromJSON(json_path):
    # Load JSON file
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Extract CGRA definition
    cgra_def = {}
    for key, value in data.pop('cgra_def', {}).items():
        cgra_def[key] = value

    # Define additional CGRA parameters
    cgra_def.setdefault("num_fu_inports", 3)
    cgra_def.setdefault("num_fu_outports", 1)
    cgra_def.setdefault("num_consts", 16)
    cgra_def.setdefault("data_width", 8)
    cgra_def.setdefault("num_register_banks", 8)
    cgra_def.setdefault("num_pred_registers", 16)
    cgra_def.setdefault("ld_locs", [1, 0, 0, 1])
    cgra_def.setdefault("st_locs", [1, 0, 0, 1])
    
    # Ensure upper limit of pred registers
    if cgra_def['num_pred_registers'] > cgra_def['num_registers']:
        cgra_def['num_pred_registers'] = cgra_def['num_registers']

    # Define the packet structure
    num_taker_ports = cgra_def['num_rd_ports']
    num_returner_ports = cgra_def['num_wr_ports'] + cgra_def['num_ld_ports'] + cgra_def['num_st_ports']

    PortRouteType = mk_bits( num_returner_ports )
    PortDelayType = mk_bits( clog2(cgra_def['num_tiles']) )  # +1 for external port
    CfgTokenizerType = mk_cfg_tokenizer_pkt(num_taker_ports,
                                            num_returner_ports,
                                            cgra_def['num_tiles'],
                                            PortRouteType,
                                            PortDelayType
                                            )

    DataType = mk_bits(cgra_def['data_width'])
    ConstImmType = mk_bits(min(8, cgra_def['data_width']))
    OperationType = mk_bits( clog2(NUM_OPTS) )
    RegAddrType = mk_bits(clog2(cgra_def['num_registers']))
    PredAddrType = mk_bits(clog2(cgra_def['num_pred_registers']))
    ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )
    TilePortType = mk_bits( clog2(cgra_def['num_tile_inports'] + 1) ) # +1 for no connection
    TileOutType = mk_bits( cgra_def['num_tile_outports'] )
    TileIdType = mk_bits( clog2(cgra_def['num_tiles']) )
    TileBitstreamType = mk_tile_bitstream_pkt(cgra_def['num_tile_inports'],
                                                cgra_def['num_tile_outports'],
                                                cgra_def['num_fu_inports'],
                                                cgra_def['num_fu_outports'],
                                                TileIdType,
                                                OperationType,
                                                DataType,
                                                RegAddrType,
                                                PredAddrType,
                                            )

    CfgBitstreamType = mk_bitstream_pkt(cgra_def['num_tiles'], TileBitstreamType)

    ThreadIdxType = mk_bits(clog2(MAX_THREAD_COUNT))
    CfgIdType = mk_bits(clog2(MAX_BITSTREAM_COUNT))
    CfgMetadataType = mk_cfg_metadata_pkt(cgra_def['num_tiles'],
                                            cgra_def['num_consts'],
                                            cgra_def['num_rd_ports'],
                                            cgra_def['num_wr_ports'],
                                            cgra_def['num_ld_ports'],
                                            cgra_def['num_st_ports'],
                                            DataType,
                                            RegAddrType,
                                            PredAddrType,
                                            CfgTokenizerType,
                                        )

    cgra_def['CfgBitstreamType'] = CfgBitstreamType
    cgra_def['CfgMetadataType'] = CfgMetadataType
    cgra_def['CfgTokenizerType'] = CfgTokenizerType
    cgra_def['TileBitstreamType'] = TileBitstreamType
    cgra_def['OperationType'] = OperationType
    cgra_def['DataType'] = DataType
    cgra_def['RegAddrType'] = RegAddrType
    cgra_def['PredAddrType'] = PredAddrType

    #####################
    # CPU Pkts
    #####################
    # Process each packet and convert to CPU packet format
    cpu_metadata_pkt = []
    cpu_bitstream_pkt = []
    for _, pkt in _iter_cfg_entries(data):
        metadata = pkt['metadata']

        # Tokenizer Pkt
        tokenizer_route_sinks = []
        tokenizer_route_lists = _augment_tokenizer_routes(
            metadata,
            cgra_def['num_rd_ports'],
            cgra_def['num_wr_ports'],
            cgra_def['num_ld_ports'],
            cgra_def['num_st_ports'],
        )
        for route in tokenizer_route_lists:
            tokenizer_route_sinks.append(PortRouteType(int(''.join(map(str, route)), 2)))
        cfg_tokenizer_pkt = CfgTokenizerType(
            token_route_sink_enable=tokenizer_route_sinks,
            token_route_delay_to_sink=[PortDelayType(delay) for delay in metadata['tokenizer']['token_route_delay_to_sink']]
        )

        # Sanitize input regs
        in_regs = []
        in_tid = []
        explicit_in_tid = metadata.get('in_tid_enable', [0] * cgra_def['num_rd_ports'])
        in_pred_regs = metadata.get('in_pred_regs', [0] * cgra_def['num_rd_ports'])
        in_pred_en = metadata.get('in_pred_en', [0] * cgra_def['num_rd_ports'])
        in_pred_inv = metadata.get('in_pred_inv', [0] * cgra_def['num_rd_ports'])
        in_const_vals = metadata.get('in_const_vals', [0] * cgra_def['num_rd_ports'])
        in_pred_reset_const_en = metadata.get('in_pred_reset_const_en', [0] * cgra_def['num_rd_ports'])

        if len(in_pred_regs) != cgra_def['num_rd_ports']:
            raise ValueError(
                f"cfg_{metadata.get('cfg_id', '?')} metadata.in_pred_regs length {len(in_pred_regs)} "
                f"does not match num_rd_ports {cgra_def['num_rd_ports']}"
            )
        if len(in_pred_en) != cgra_def['num_rd_ports']:
            raise ValueError(
                f"cfg_{metadata.get('cfg_id', '?')} metadata.in_pred_en length {len(in_pred_en)} "
                f"does not match num_rd_ports {cgra_def['num_rd_ports']}"
            )
        if len(in_pred_inv) != cgra_def['num_rd_ports']:
            raise ValueError(
                f"cfg_{metadata.get('cfg_id', '?')} metadata.in_pred_inv length {len(in_pred_inv)} "
                f"does not match num_rd_ports {cgra_def['num_rd_ports']}"
            )
        if len(in_const_vals) != cgra_def['num_rd_ports']:
            raise ValueError(
                f"cfg_{metadata.get('cfg_id', '?')} metadata.in_const_vals length {len(in_const_vals)} "
                f"does not match num_rd_ports {cgra_def['num_rd_ports']}"
            )
        if len(in_pred_reset_const_en) != cgra_def['num_rd_ports']:
            raise ValueError(
                f"cfg_{metadata.get('cfg_id', '?')} metadata.in_pred_reset_const_en length {len(in_pred_reset_const_en)} "
                f"does not match num_rd_ports {cgra_def['num_rd_ports']}"
            )

        for idx, reg in enumerate(metadata['in_regs']):
            if reg == 'tid':
                in_regs.append(0)
                in_tid.append(1)
            else:
                in_regs.append(reg)
                in_tid.append(explicit_in_tid[idx])

        thread_span, thread_count_min, thread_count_max = _get_thread_range(
            metadata,
            overflow_thread_cap=cgra_def['num_wr_ports'],
        )

        # Metadata Pkt
        cfg_metadata_pkt = CfgMetadataType(
            cmd = metadata.get('cmd', CMD_CONFIG),
            tile_load_count = metadata.get('tile_load_count', 0),
            pred_tile_valid = [Bits1(bit) for bit in metadata['pred_tile_valid']],
            ld_enable = [Bits1(bit) for bit in metadata['ld_enable']],
            st_enable = [Bits1(bit) for bit in metadata['st_enable']],
            ld_reg_addr = [RegAddrType(bit) for bit in metadata['ld_reg_addr']],
            in_regs = [RegAddrType(bit) for bit in in_regs],
            in_regs_val = [Bits1(bit) for bit in metadata['in_regs_val']],
            in_tid_enable = [Bits1(bit) for bit in in_tid],
            in_pred_regs = [PredAddrType(bit) for bit in in_pred_regs],
            in_pred_en = [Bits1(bit) for bit in in_pred_en],
            in_pred_inv = [Bits1(bit) for bit in in_pred_inv],
            in_const_vals = [
                ConstImmType(max(0, min(int(bit), (1 << ConstImmType.nbits) - 1)))
                for bit in in_const_vals
            ],
            in_pred_reset_const_en = [Bits1(bit) for bit in in_pred_reset_const_en],
            out_regs = [RegAddrType(bit) for bit in metadata['out_regs']],
            out_regs_val = [Bits1(bit) for bit in metadata['out_regs_val']],
            out_pred_regs = [PredAddrType(bit) for bit in metadata.get('out_pred_regs', [0] * cgra_def['num_wr_ports'])],
            out_pred_regs_val = [Bits1(bit) for bit in metadata.get('out_pred_regs_val', [0] * cgra_def['num_wr_ports'])],
            tokenizer_cfg = cfg_tokenizer_pkt,
            cfg_id = CfgIdType(metadata['cfg_id']),
            br_id = CfgIdType(metadata['br_id']),
            thread_count_min = ThreadIdxType(thread_count_min),
            thread_count_max = ThreadIdxType(thread_count_max),
            start_cfg = Bits1(metadata['start_cfg']),
            end_cfg = Bits1(metadata['end_cfg']),
            branch_en = Bits1(metadata.get('branch_en', 0)),
            branch_has_else = Bits1(metadata.get('branch_has_else', 0)),
            branch_backedge_sel = metadata.get('branch_backedge_sel', 0),
            pred_reg_id = PredAddrType(metadata.get('pred_reg_id', 0)),
            branch_true_cfg_id = CfgIdType(metadata.get('branch_true_cfg_id', 0)),
            branch_false_cfg_id = CfgIdType(metadata.get('branch_false_cfg_id', 0)),
            reconverge_cfg_id = CfgIdType(metadata.get('reconverge_cfg_id', 0)),
            loop_en = Bits1(metadata.get('loop_en', 0)),
            loop_start_cfg_id = CfgIdType(metadata.get('loop_start_cfg_id', 0)),
            loop_exit_cfg_id = CfgIdType(metadata.get('loop_exit_cfg_id', 0)),
            loop_max = ThreadIdxType(metadata.get('loop_max', 0)),
        )

        # Tile Bitstream Pkts
        tile_bitstream_pkts = {}
        for tile in pkt['bitstream'].values():
            tile_id = TileIdType(tile['id'])
            if tile['opt_type'] == 'OPT_NAH':
                tile_bitstream_pkts[tile['id']] = TileBitstreamType(
                    tile_id = tile_id,
                    opt_type = OPT_NAH
                )
            else:
                tile_in_route = []
                tile_out_route = '0' * cgra_def['num_tile_outports']
                tile_pred_route = '0' * cgra_def['num_tile_outports']
                pred_based_sel_in_to_out_route = 0  # Default to no pred forwarding
                tile_fwd_route = [
                    TileOutType(int(''.join(map(str, route_bits)), 2))
                    for route_bits in tile.get(
                        'tile_fwd_route',
                        _default_tile_fwd_route(
                            cgra_def['num_tile_inports'],
                            cgra_def['num_tile_outports'],
                        ),
                    )
                ]
                # Input Routes
                if "tile_in_route" not in tile:
                    tile['tile_in_route'] = [TilePortType(0)] * cgra_def['num_tile_inports']
                else:
                    for port in tile['tile_in_route']:
                        if port:
                            tile_in_route.append(TilePortType(TilePortEnum[port].value + 1))  # +1 for external port
                        else:
                            tile_in_route.append(TilePortType(0))

                # Output Routes
                if "tile_out_route" in tile:
                    for port in tile['tile_out_route']:
                        if port:
                            idx = TilePortEnum[port].value
                            tile_out_route = tile_out_route[:idx] + '1' + tile_out_route[idx+1:]
                
                # tile_out_shift_amounts
                max_shift_val = (1 << ShiftAmountType.nbits) - 1
                if "tile_out_shift_amounts" not in tile:
                    tile['tile_out_shift_amounts'] = [0] * cgra_def['num_tile_outports']
                else:
                    tile_out_shift_amounts = [
                        ShiftAmountType(max(0, min(int(val), max_shift_val)))
                        for val in tile['tile_out_shift_amounts']
                    ]

                # Pred Routes
                if "tile_pred_route" in tile:
                    for port in tile['tile_pred_route']:
                        if port:
                            idx = TilePortEnum[port].value
                            tile_pred_route = tile_pred_route[:idx] + '1' + tile_pred_route[idx+1:]
                
                # Pred Forwarding
                pred_sel_route = tile.get('pred_based_sel_in_to_out_route', '')
                if pred_sel_route:
                    pred_based_sel_in_to_out_route = TilePortEnum[pred_sel_route].value

                # Append Tile Bitstream Pkt
                tile_bitstream_pkts[tile['id']] = TileBitstreamType(
                    tile_id = tile_id,
                    tile_in_route = tile_in_route,
                    tile_out_route = int(tile_out_route, 2),
                    tile_out_shift_amounts = tile_out_shift_amounts,
                    tile_pred_route = int(tile_pred_route, 2),
                    tile_fwd_route = tile_fwd_route,
                    const_val = tile.get('const_val', 0),
                    pred_based_sel_in_to_out_route = pred_based_sel_in_to_out_route,
                    pred_gen = Bits1(tile.get('pred_gen', 0)),
                    opt_type = _resolve_opt_type(tile['opt_type'])
                )
        
        # No Longer needed
        # Cfg Bitstream Pkt
        # cfg_bitstream_pkt = CfgBitstreamType(bitstream = tile_bitstream_pkts)

        ordered_tile_pkts = []
        for i in range(cgra_def['num_tile_rows']):
            row = [
                tile_bitstream_pkts[i*cgra_def['num_tile_cols'] + j]
                for j in range(cgra_def['num_tile_cols'])
            ]
            ordered_tile_pkts += row[::-1] if i % 2 == 1 else row

        tile_pkts_to_send = [
            tile_pkt for tile_pkt in ordered_tile_pkts[::-1]
            if tile_pkt.opt_type != OPT_NAH
        ]
        expected_tile_load_count = int(cfg_metadata_pkt.tile_load_count)
        if len(tile_pkts_to_send) != expected_tile_load_count:
            raise ValueError(
                f"Config {int(cfg_metadata_pkt.cfg_id)} expected {expected_tile_load_count} active tiles "
                f"but JSON bitstream contains {len(tile_pkts_to_send)} non-OPT_NAH tiles"
            )

        cpu_metadata_pkt.append(cfg_metadata_pkt)
        cpu_bitstream_pkt += tile_pkts_to_send

    # Append the launch pkt
    cpu_metadata_pkt.append(CfgMetadataType(cmd = CMD_LAUNCH))
    # cpu_bitstream_pkt.append(CfgBitstreamType())

    #####################
    # Ld Pkts
    #####################
    ld_pkts = defaultdict(list)
    for _, pkt in _iter_cfg_entries(data):
        thread_span, _, _ = _get_thread_range(
            pkt['metadata'],
            overflow_thread_cap=cgra_def['num_wr_ports'],
        )
        for index, ld_enable in enumerate(pkt['metadata']['ld_enable']):
            if ld_enable:
                ld_pkts[index] += [5] * (thread_span*20)  # Dummy ld pkt

    #####################
    # St Pkts
    #####################
    st_pkts = defaultdict(int)
    for _, pkt in _iter_cfg_entries(data):
        thread_span, _, _ = _get_thread_range(
            pkt['metadata'],
            overflow_thread_cap=cgra_def['num_wr_ports'],
        )
        for index, st_enable in enumerate(pkt['metadata']['st_enable']):
            if st_enable:
                st_pkts[index] += thread_span  # Dummy st pkt count

    expected_cpu_pkts = [1]
    
    return cgra_def, cpu_metadata_pkt, cpu_bitstream_pkt, ld_pkts, st_pkts, expected_cpu_pkts
        
