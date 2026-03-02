

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

def generateCPUPktFromJSON(json_path):
    # Load JSON file
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    # Extract CGRA definition
    cgra_def = {}
    for key, value in data.pop('cgra_def', {}).items():
        cgra_def[key] = value

    # Define additional CGRA parameters
    cgra_def.update({
        "num_fu_inports": 3,
        "num_fu_outports": 1,
        "num_consts": 16,
        "data_width": 8,
        "num_register_banks": 8,
        "num_pred_registers": 16,
    })
    
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
    OperationType = mk_bits( clog2(NUM_OPTS) )
    RegAddrType = mk_bits(clog2(cgra_def['num_registers']))
    PredAddrType = mk_bits(clog2(cgra_def['num_pred_registers']))
    ShiftAmountType = mk_bits( clog2(SHIFT_REGISTER_SIZE) )
    TilePortType = mk_bits( clog2(cgra_def['num_tile_inports'] + 1) ) # +1 for no connection
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

    ThreadCountType = mk_bits(clog2(MAX_THREAD_COUNT))
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
    for key, pkt in data.items():
        # Tokenizer Pkt
        tokenizer_route_sinks = []
        for route in pkt['metadata']['tokenizer']['token_route_sink_enable']:
            tokenizer_route_sinks.append(PortRouteType(int(''.join(map(str, route)), 2)))
        cfg_tokenizer_pkt = CfgTokenizerType(
            token_route_sink_enable=tokenizer_route_sinks,
            token_route_delay_to_sink=[PortDelayType(delay) for delay in pkt['metadata']['tokenizer']['token_route_delay_to_sink']]
        )

        # Sanitize input regs
        in_regs = []
        in_tid = []
        for reg in pkt['metadata']['in_regs']:
            if reg == 'tid':
                in_regs.append(0)
                in_tid.append(1)
            else:
                in_regs.append(reg)
                in_tid.append(0)

        # Metadata Pkt
        cfg_metadata_pkt = CfgMetadataType(
            cmd = CMD_CONFIG,
            pred_tile_valid = [Bits1(bit) for bit in pkt['metadata']['pred_tile_valid']],
            ld_enable = [Bits1(bit) for bit in pkt['metadata']['ld_enable']],
            st_enable = [Bits1(bit) for bit in pkt['metadata']['st_enable']],
            ld_reg_addr = [RegAddrType(bit) for bit in pkt['metadata']['ld_reg_addr']],
            in_regs = [RegAddrType(bit) for bit in in_regs],
            in_regs_val = [Bits1(bit) for bit in pkt['metadata']['in_regs_val']],
            in_tid_enable = [Bits1(bit) for bit in in_tid],
            out_regs = [RegAddrType(bit) for bit in pkt['metadata']['out_regs']],
            out_regs_val = [Bits1(bit) for bit in pkt['metadata']['out_regs_val']],
            tokenizer_cfg = cfg_tokenizer_pkt,
            cfg_id = CfgIdType(pkt['metadata']['cfg_id']),
            br_id = CfgIdType(pkt['metadata']['br_id']),
            thread_count = ThreadCountType(pkt['metadata']['thread_count']),
            start_cfg = Bits1(pkt['metadata']['start_cfg']),
            end_cfg = Bits1(pkt['metadata']['end_cfg']),
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
                pred_fwd_route = 0  # Default to no pred forwarding
                # Input Routes
                for port in tile['tile_in_route']:
                    if port:
                        tile_in_route.append(TilePortType(TilePortEnum[port].value + 1))  # +1 for external port
                    else:
                        tile_in_route.append(TilePortType(0))

                # Output Routes
                for port in tile['tile_out_route']:
                    idx = TilePortEnum[port].value
                    tile_out_route = tile_out_route[:idx] + '1' + tile_out_route[idx+1:]
                
                # tile_out_shift_amounts
                tile_out_shift_amounts = [ShiftAmountType(val) for val in tile['tile_out_shift_amounts']]

                # Pred Routes
                for port in tile['tile_pred_route']:
                    idx = TilePortEnum[port].value
                    tile_pred_route = tile_pred_route[:idx] + '1' + tile_pred_route[idx+1:]
                
                # Pred Forwarding
                if tile['pred_fwd_route']:
                    pred_fwd_route = TilePortEnum[tile['pred_fwd_route']].value

                # Append Tile Bitstream Pkt
                tile_bitstream_pkts[tile['id']] = TileBitstreamType(
                    tile_id = tile_id,
                    tile_in_route = tile_in_route,
                    tile_out_route = int(tile_out_route, 2),
                    tile_out_shift_amounts = tile_out_shift_amounts,
                    tile_pred_route = int(tile_pred_route, 2),
                    const_val = tile['const_val'],
                    pred_fwd_route = pred_fwd_route,
                    pred_gen = tile['pred_gen'],
                    opt_type = eval(tile['opt_type'])
                )
        
        # No Longer needed
        # Cfg Bitstream Pkt
        # cfg_bitstream_pkt = CfgBitstreamType(bitstream = tile_bitstream_pkts)

        # Full CPU Pkt
        cpu_metadata_pkt.append(cfg_metadata_pkt)
        bitstream_pkts_before_reverse = []
        for i in range(cgra_def['num_tile_rows']):
            row = [
                tile_bitstream_pkts[i*cgra_def['num_tile_cols'] + j]
                for j in range(cgra_def['num_tile_cols'])
            ]

            bitstream_pkts_before_reverse += row[::-1] if i % 2 == 1 else row
        cpu_bitstream_pkt += bitstream_pkts_before_reverse[::-1]

    # Append the launch pkt
    cpu_metadata_pkt.append(CfgMetadataType(cmd = CMD_LAUNCH))
    # cpu_bitstream_pkt.append(CfgBitstreamType())

    #####################
    # Ld Pkts
    #####################
    ld_pkts = defaultdict(list)
    for pkt in data.values():
        thread_count = pkt['metadata']['thread_count']
        for index, ld_enable in enumerate(pkt['metadata']['ld_enable']):
            if ld_enable:
                ld_pkts[index] += [5] * thread_count  # Dummy ld pkt

    #####################
    # St Pkts
    #####################
    st_pkts = defaultdict(int)
    for pkt in data.values():
        thread_count = pkt['metadata']['thread_count']
        for index, st_enable in enumerate(pkt['metadata']['st_enable']):
            if st_enable:
                st_pkts[index] += 1  # Dummy st pkt

    expected_cpu_pkts = [1]
    
    return cgra_def, cpu_metadata_pkt, cpu_bitstream_pkt, ld_pkts, st_pkts, expected_cpu_pkts
        
