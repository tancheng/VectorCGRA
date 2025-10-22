from imp import source_from_cache
from locale import D_FMT
from multiprocessing import Value
import sys
from uu import Error
from _pytest import config
import yaml

from lib.opt_type import *

# from ... import *  # TODO: import the correct file of the opCodes of VectorCGRA

yaml_to_VectorCGRA_map = {
    "CONSTANT": None, # ?
    "ADD": OPT_ADD,
    "MUL": OPT_MUL,
    "SUB": OPT_SUB,
    "DIV": OPT_DIV,
    "REM": OPT_REM,
    "FADD": OPT_FADD,
    "FSUB": OPT_FSUB,
    "FMUL": OPT_FMUL,
    "FDIV": None, # ?
    "OR": OPT_OR,
    "NOT": OPT_NOT,
    "ICMP": None, # ?
    "FCMP": None, # ?
    "SEL": OPT_SEL,
    "CAST": None, # ?
    "SEXT": None, # ?
    "ZEXT": None, # ?
    "SHL": OPT_LLS,
    "VFMUL": None, # ?
    "FADD_FADD": None, #?
    "FMUL_FADD": None, #?
    "DATA_MOV": None, #?
    "CTRL_MOV": None, #?
    "RESERVE": None, #?
    "GRANT_PREDICATE": None, #?
    "GRANT_ALWAYS": None, #?
    "GRANT_ONCE": None, #?
    "PHI": OPT_PHI,
    "LOOP_CONTROL": None, #?
}


def _type(Operand):
    if Operand[0] == "$":
        return 'REG'
    elif Operand[0] in ['NORTH', 'SOUTH', 'WEST', 'EAST']:
        return 'PORT'
    else:
        return 'IMM'

def _is_take_up_fu_operation(operation):
    if operation['opcode'] == 'MOV':
        if len(operation['srcOperands']) != 1:
            raise ValueError("MOV operation must have exactly one source operand")
        elif _type(operation['srcOperands'][0]) == 'REG':
            return True
        else:
            return False
    else:
        return True
    
def _reg_cluster_no_of(operand):
    if operand[0] == "$":
        return int(operand[1:]) / 8
    else:
        raise ValueError("Operand is not a register")

def _reg_cluster_intra_index_of(operand):
    if operand[0] == "$":
        return int(operand[1:]) % 8
    else:
        raise ValueError("Operand is not a register")

FROM_NOWHERE = 0
FROM_PORT = 1
FROM_FU = 2
FROM_CONSTANT_QUEUE = 3 # not used by now

OPR_FROM_PORT = 0
OPR_FROM_REGISTER = 1

class InstructionSignals:
    # to make signal of single instruction

    def __init__(self, 
                 # input
                 id_,
                 operations,
                 opcode_in_EIR,
                 ctrl_addr,
                 # types
                 IntraCgraPktType, 
                 CgraPayloadType, 
                 TileInType, 
                 FuOutType, 
                 configType, 
                 CtrlType,
                 FuInType,
                 B1Type,
                 B2Type):
        # types
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.configType = configType
        self.CtrlType = CtrlType
        self.FuInType = FuInType
        self.B1Type = B1Type
        self.B2Type = B2Type
        
        # inputs
        self.id_ = id_
        self.operations = operations
        self.OpCode = opcode_in_EIR
        self.ctrl_addr = ctrl_addr
        
        # States
        self.TileInParams = [-1, -1, -1, -1, -1, -1, -1, -1]
        self.FuOutParams = [0, 0, 0, 0, 0, 0, 0, 0]
        self.read_from_reg = [-1, -1, -1, -1]
        self.read_from_reg_idx = [-1, -1, -1, -1]
        self.write_to_reg = [-1, -1, -1, -1]
        self.write_to_reg_idx = [-1, -1, -1, -1]
        self.shuffle_fu_operand_input_index = [-1, -1, -1, -1]

        
    def buildCtrlPkt(self) -> list: # return the const needed to put into the const queue
        # you must call buildCtrlPkt before makeCtrlPkt, and for a Tile's signal, you must call buildCtrlPkt in order.
        try:
            take_up_fu_operation_idx = -1
            for idx, operation in enumerate(self.operations):
                if _is_take_up_fu_operation(operation):
                    if take_up_fu_operation_idx != -1:
                        raise ValueError("Only one take up fu operation is allowed")
                    take_up_fu_operation_idx = idx
            
            self.opCode = yaml_to_VectorCGRA_map[self.operations[take_up_fu_operation_idx]['opcode']]
            const_operands = []

            for operation in self.operations: # for each operation in the instruction
                
                operation_opcode = operation['opcode']
                src_operands = operation['srcOperands']
                dst_operands = operation['dstOperands']
                
                # find all the const
                for index, src_operand in enumerate(src_operands):
                    if _type(src_operand) == 'IMM':
                        const_operands.append(src_operand)
                        # delete it from the src_operands since it is implicit in vectorCGRA
                        del src_operands[index]
                
                for index, src_operand in enumerate(src_operands):
                    if _type(src_operand) == 'REG':
                        cluster_no = _reg_cluster_no_of(src_operand)
                        intra_index = _reg_cluster_intra_index_of(src_operand)
                        if self.read_from_reg_idx[cluster_no] != -1 and self.read_from_reg_idx[cluster_no] != intra_index:
                            raise ValueError(f"Collision when reading from register in read_from_reg_idx, when translate the operation {operation} to VectorCGRA")
                        self.read_from_reg[cluster_no] = OPR_FROM_REGISTER
                        self.read_from_reg_idx[cluster_no] = intra_index
                        if self.shuffle_fu_operand_input_index[cluster_no] != -1:
                            raise ValueError(f"Collision when reading from register in shuffle_fu_operand_input_index, when translate the operation {operation} to VectorCGRA")
                        self.shuffle_fu_operand_input_index[cluster_no] = index # make the idx arg of the 
                    if _type(src_operand) == 'PORT':
                        if src_operand['operand'] == 'NORTH':
                            port_in_xbar_idx = 1
                        elif src_operand['operand'] == 'SOUTH':
                            port_in_xbar_idx = 2
                        elif src_operand['operand'] == 'WEST':
                            port_in_xbar_idx = 3
                        elif src_operand['operand'] == 'EAST':
                            port_in_xbar_idx = 4
                        if self.TileInParams[index + 4] != -1:
                            raise ValueError(f"Collision in reading from port in TileInParams, when translate the operation {operation} to VectorCGRA")
                        self.TileInParams[index + 4] = port_in_xbar_idx
                        self.read_from_reg[index] = OPR_FROM_PORT
                    if _type(src_operand) == 'IMM':
                        raise NotImplementedError("IMM src operand is not supported yet")
                    
                for index, dst_operand in enumerate(dst_operands):
                    if _type(dst_operand) == 'REG':
                        cluster_no = _reg_cluster_no_of(dst_operand)
                        intra_index = _reg_cluster_intra_index_of(dst_operand)
                        if self.write_to_reg_idx[cluster_no] != -1 and self.write_to_reg_idx[cluster_no] != intra_index:
                            raise ValueError(f"Collision when writing to register in write_to_reg_idx, when translate the operation {operation} to VectorCGRA")
                        self.write_to_reg[cluster_no] = FROM_FU
                        self.write_to_reg_idx[cluster_no] = intra_index
                    elif _type(dst_operand) == 'PORT':
                        if dst_operand['operand'] == 'NORTH':
                            port_out_xbar_idx = 0
                        elif dst_operand['operand'] == 'SOUTH':
                            port_out_xbar_idx = 1
                        elif dst_operand['operand'] == 'WEST':
                            port_out_xbar_idx = 2
                        elif dst_operand['operand'] == 'EAST':
                            port_out_xbar_idx = 3
                        if self.FuOutParams[index] != -1:
                            raise ValueError(f"Collision in writing to port in FuOutParams, when translate the operation {operation} to VectorCGRA")
                        self.FuOutParams[port_out_xbar_idx] = index
                    else:
                        raise ValueError(f"Unsupported type of dst operand, when translate the operation {operation} to VectorCGRA")
        
        except Exception as e:
            print(f"Error in making ctrl pkt: {e}")
            return None
        
        def makeCtrlPkt(self):
            # make fu_in_code
            for idx, fu_in_code in enumerate(self.shuffle_fu_operand_input_index):
                if fu_in_code == -1:
                    self.shuffle_fu_operand_input_index[idx] = 0 # 0 or idle inport of ALU?
            fu_in_code_made = [self.FuInType(x) for x in self.shuffle_fu_operand_input_index]
            
            # make TileIn
            TileIn_made = [self.TileInType(x) for x in self.TileInParams]
            FuOut_made = [self.FuOutType(x) for x in self.FuOutParams]
            
            # made write reg from code
            for idx, write_to_reg in enumerate(self.write_to_reg):
                if write_to_reg == -1:
                    self.write_to_reg[idx] = FROM_NOWHERE
            write_reg_from_made = [self.B1Type(x) for x in self.write_to_reg]
            
            for idx, write_to_reg_idx in enumerate(self.write_to_reg_idx):
                if write_to_reg_idx == -1:
                    self.write_to_reg_idx[idx] = 0
            write_reg_idx_made = [self.B2Type(x) for x in self.write_to_reg_idx]
            
            # make read reg from code
            for idx, read_from_reg in enumerate(self.read_from_reg):
                if read_from_reg == -1:
                    self.read_from_reg[idx] = OPR_FROM_PORT

            read_reg_from_made = [self.B1Type(x) for x in self.read_from_reg]
            
            for idx, read_from_reg_idx in enumerate(self.read_from_reg_idx):
                if read_from_reg_idx == -1:
                    self.read_from_reg_idx[idx] = 0
            read_reg_idx_made = [self.B2Type(x) for x in self.read_from_reg_idx]
            
            # make FuOut
            pkt = self.IntraCgraPktType(0, self.id_, 
                                        payload = self.CgraPayloadType(self.configType, self.ctrl_addr, 
                                                                       ctrl = self.CtrlType(self.opCode,
                                                                                            fu_in_code_made,
                                                                                            TileIn_made,
                                                                                            FuOut_made,
                                                                                            write_reg_from_made,
                                                                                            write_reg_idx_made,
                                                                                            read_reg_from_made,
                                                                                            read_reg_idx_made,
                                                                                            )))
            return pkt

class TileSignals:
    def __init__(self,
                CtrlType, 
                IntraCgraPktType, 
                CgraPayloadType, 
                TileInType, 
                FuOutType, 
                config, 
                fuInCode, 
                id_, 
                loop_times,
                ii,
                instructions):
        self.CtrlType = CtrlType
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.config = config
        self.fuInCode = fuInCode
        self.id_ = id_
        self.instructions = instructions
        self.loop_times = loop_times
        self.ii = ii
    
    def makeTileSignals(self):
        consts = []
        all_signals = []
        
        # build all the instruction signals and get all the const
        for instructions in instructions:
            instruction_signals = InstructionSignals(instructions, self.CtrlType, self.IntraCgraPktType, self.CgraPayloadType, self.TileInType, self.FuOutType, self.config, self.fuInCode, self.id_)
            const = instruction_signals.buildCtrlPkt()
            if const is not None:
                consts.extend(const)
        
        # make the const signals
        for idx, const in enumerate(consts):
            const_pkt = self.IntraCgraPktType(0, self.id_, 
                                              payload = self.CgraPayloadType(CMD_CONST,
                                                                             data = DataType(const, 1)))
            all_signals.append(const_pkt)
            
        # make the pre-configuration
        ii_pkt = self.IntraCgraPktType(0, self.id_, 
                                       payload = self.CgraPayloadType(CMD_CONFIG_COUNT_PER_ITER,
                                                                      data = DataType(self.ii, 1)))
        all_signals.append(ii_pkt)
        loop_times_pkt = self.IntraCgraPktType(0, self.id_, 
                                               payload = self.CgraPayloadType(CMD_CONFIG_TOTAL_CTRL_COUNT,
                                                                              data = DataType(self.loop_times, 1)))
        all_signals.append(loop_times_pkt)
        
        return all_signals
        
class ScriptFactory:
    FromFu = 0
    FromRouting = 1
    
    def __init__(self, path, CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, fuInCode, id_, ii):
        self.yaml_struct = yaml.load(open(path, 'r'), Loader=yaml.FullLoader)
        self.CtrlType = CtrlType
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.config = config
        self.fuInCode = fuInCode
    
    def makeVectorCGRAPkts(self, ScriptInsts, CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, fuInCode, id_, FromFuOrRouting = FromRouting): #False means from routing inst
        
        pkts = {}
        cores = self.yaml_struct['array_config']['cores']
        
        
        for core in cores:
            x, y = core['x'], core['y']
            entry = self.core['entries'][0]
            instructions = entry['instructions']
            
            TileSignals = TileSignals(CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, fuInCode, id_, loop_times, ii, instructions)
            tile_signals = TileSignals.makeTileSignals()
            pkts[(x, y)] = tile_signals
            
        return pkts
    