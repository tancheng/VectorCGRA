import sys
import os
import yaml

# Add project root to path to allow imports from lib
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
    "GRANT_PREDICATE": OPT_GRT_PRED,
    "GRANT_ALWAYS": None, #?
    "GRANT_ONCE": None, #?
    "PHI": OPT_PHI,
    "LOOP_CONTROL": None, #?
    "PHI_CONST": OPT_PHI_CONST, 
    
    "RETURN": OPT_RET,
    "LDD": OPT_LD,
    "NE": OPT_NE,
}

yaml_to_VectorCGRA_map_const = {
    "NE": OPT_NE_CONST,
    "ADD": OPT_ADD_CONST,
}


def _type(Operand):
    impl = Operand['operand']
    if impl[0] == "$":
        return 'REG'
    elif impl.upper() in ['NORTH', 'SOUTH', 'WEST', 'EAST', 'SOUTHEAST', 'SOUTHWEST', 'NORTHWEST', 'NORTHEAST']:
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
    
def _reg_cluster_no_of(operand): # start from 1
    impl = operand['operand']
    if impl[0] == "$":
        return int(impl[1:]) // 8 + 1
    else:
        raise ValueError("Operand is not a register")

def _reg_cluster_intra_index_of(operand):
    impl = operand['operand']
    if impl[0] == "$":
        return int(impl[1:]) % 8
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
                 CMD_CONFIG_input, 
                 CtrlType,
                 FuInType,
                 B1Type,
                 B2Type):
        # types
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.CMD_CONFIG_ = CMD_CONFIG_input
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
        self.FuOutParams = [-1, -1, -1, -1, -1, -1, -1, -1]
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
            
            # TODO: fix logic here
                  
            take_up_fu_operation = self.operations[take_up_fu_operation_idx]
            has_const = False
            # if has src_operands, check if has const
            try:
                src_operands = take_up_fu_operation['src_operands']
            except Exception as e:
                src_operands = []
            for src_operand in src_operands:
                if _type(src_operand) == 'IMM':
                    has_const = True
                    break 
                
            if take_up_fu_operation['opcode'] == 'PHI_CONST':
                has_const = False # PHI_CONST is special.
            
            if has_const:
                self.opCode = yaml_to_VectorCGRA_map_const[self.operations[take_up_fu_operation_idx]['opcode']]
            else:
                self.opCode = yaml_to_VectorCGRA_map[self.operations[take_up_fu_operation_idx]['opcode']]

            const_operands = []

            for operation in self.operations: # for each operation in the instruction
                
                print("Working on operation: ", operation)
                
                operation_opcode = operation['opcode']
                try:
                    src_operands = operation['src_operands']
                except Exception as e:
                    src_operands = []
                try:
                    dst_operands = operation['dst_operands']
                except Exception as e:
                    dst_operands = []
                
                # find all the const
                for index, src_operand in enumerate(src_operands):
                    if _type(src_operand) == 'IMM':
                        const_operands.append(src_operand)
                        # delete it from the src_operands since it is implicit in vectorCGRA
                        del src_operands[index]
                
                for index, src_operand in enumerate(src_operands):
                    if _type(src_operand) == 'REG':
                        print(f">>> index {index} is REG")
                        cluster_no = _reg_cluster_no_of(src_operand)
                        intra_index = _reg_cluster_intra_index_of(src_operand)
                        if self.read_from_reg_idx[cluster_no - 1] != -1 and self.read_from_reg_idx[cluster_no - 1] != intra_index:
                            raise ValueError(f"Collision when reading from register in read_from_reg_idx, when translate the operation {operation} to VectorCGRA")
                        self.read_from_reg[cluster_no - 1] = OPR_FROM_REGISTER
                        self.read_from_reg_idx[cluster_no - 1] = intra_index
                        if self.shuffle_fu_operand_input_index[index] != -1:
                            raise ValueError(f"Collision when reading from register in shuffle_fu_operand_input_index, when translate the operation {operation} to VectorCGRA")
                        self.shuffle_fu_operand_input_index[index] = cluster_no # shuffle the data to the correct inport of the FU from the register
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
                        if self.write_to_reg_idx[cluster_no - 1] != -1 and self.write_to_reg_idx[cluster_no - 1] != intra_index:
                            raise ValueError(f"Collision when writing to register in write_to_reg_idx, when translate the operation {operation} to VectorCGRA")
                        self.write_to_reg[cluster_no - 1] = FROM_FU
                        self.write_to_reg_idx[cluster_no - 1] = intra_index
                        if self.FuOutParams[cluster_no + 3] != -1:
                            raise ValueError(f"Collision in writing result to register, when translate the operation {operation} to VectorCGRA")
                        self.FuOutParams[cluster_no + 3] = 1
                    elif _type(dst_operand) == 'PORT':
                        if dst_operand['operand'] == 'NORTH':
                            port_out_xbar_idx = 0
                        elif dst_operand['operand'] == 'SOUTH':
                            port_out_xbar_idx = 1
                        elif dst_operand['operand'] == 'WEST':
                            port_out_xbar_idx = 2
                        elif dst_operand['operand'] == 'EAST':
                            port_out_xbar_idx = 3
                        if self.FuOutParams[port_out_xbar_idx] != -1:
                            raise ValueError(f"Collision in writing to port {dst_operand} in FuOutParams, when translate the operation {operation} to VectorCGRA")
                        print(f">>> FuOutParams[{port_out_xbar_idx}] = {index + 1}")
                        self.FuOutParams[port_out_xbar_idx] = 1 # we do not support multiple results 
                    else:
                        raise ValueError(f"Unsupported type of dst operand {dst_operand}, when translate the operation {operation} to VectorCGRA")
        
        except Exception as e:
            print(f"Error in making ctrl pkt: {e}")
            raise e
            return None
        return const_operands
        
    def makeCtrlPkt(self):
        # make fu_in_code
        for idx, fu_in_code in enumerate(self.shuffle_fu_operand_input_index):
            if fu_in_code == -1:
                self.shuffle_fu_operand_input_index[idx] = idx + 1 # 0 or idle inport of ALU?
        fu_in_code_made = [self.FuInType(x) for x in self.shuffle_fu_operand_input_index] # is it correct?
        
        # make TileIn
        for idx, tile_in_param in enumerate(self.TileInParams):
            if tile_in_param == -1:
                self.TileInParams[idx] = 0
        TileIn_made = [self.TileInType(x) for x in self.TileInParams]
        for idx, fu_out_param in enumerate(self.FuOutParams):
            if fu_out_param == -1:
                self.FuOutParams[idx] = 0
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
                                    payload = self.CgraPayloadType(self.CMD_CONFIG_, self.ctrl_addr, 
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
                CMD_CONFIG_input, 
                FuInType, 
                id_, 
                loop_times,
                ii,
                instructions,
                CMD_CONST_input,
                CMD_CONFIG_COUNT_PER_ITER_input,
                CMD_CONFIG_TOTAL_CTRL_COUNT_input,
                CMD_CONFIG_PROLOGUE_FU_input,
                CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input,
                CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input,
                CMD_LAUNCH_input,
                DataType,
                B1Type,
                B2Type):
        self.CtrlType = CtrlType
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.CMD_CONFIG_ = CMD_CONFIG_input
        self.FuInType = FuInType
        self.id_ = id_
        self.instructions = instructions
        self.loop_times = loop_times
        self.ii = ii
        self.B1Type = B1Type
        self.B2Type = B2Type
        self.DataType = DataType
        # constants
        self.CMD_CONST_ = CMD_CONST_input
        self.CMD_CONFIG_COUNT_PER_ITER_ = CMD_CONFIG_COUNT_PER_ITER_input
        self.CMD_CONFIG_TOTAL_CTRL_COUNT_ = CMD_CONFIG_TOTAL_CTRL_COUNT_input
        
        self.CMD_CONFIG_PROLOGUE_FU_ = CMD_CONFIG_PROLOGUE_FU_input
        self.CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_ = CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input
        self.CMD_CONFIG_PROLOGUE_FU_CROSSBAR_ = CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input
        
        self.CMD_LAUNCH_ = CMD_LAUNCH_input
        
        
    def makeProloguePackets(self, instruction):
        print(f"Making prologue packets for instruction {instruction}")
        pkts = []
        pkts.append(self.makePrologueFUPackets(instruction)) # always prologue FU
        take_up_fu_operation_idx = -1
        for idx, operation in enumerate(instruction['operations']):
            if _is_take_up_fu_operation(operation):
                if take_up_fu_operation_idx != -1:
                    raise ValueError("Only one take up fu operation is allowed")
                take_up_fu_operation_idx = idx
        take_up_fu_operation = None  
        if take_up_fu_operation_idx != -1:
            take_up_fu_operation = instruction['operations'][take_up_fu_operation_idx]
            # TODO: fix the logic for only having non-take up fu operation
        else:
            raise ValueError("No take up fu operation found")
        try:
            src_operands = take_up_fu_operation['src_operands']
        except Exception as e:
            src_operands = []
        for src_operand in src_operands:
            if _type(src_operand) == 'PORT':
                print(f"src_operand is PORT, add Prologue. {src_operand}")
                if src_operand['operand'] == 'NORTH':
                    routing_xbar_idx = 0 # here is from 0, strange.
                elif src_operand['operand'] == 'SOUTH':
                    routing_xbar_idx = 1
                elif src_operand['operand'] == 'WEST':
                    routing_xbar_idx = 2
                elif src_operand['operand'] == 'EAST':
                    routing_xbar_idx = 3
                pkts.append(self.makePrologueRoutingCrossbarPackets(instruction, routing_xbar_idx))
        
        try:
            dst_operands = take_up_fu_operation['dst_operands']
        except Exception as e:
            dst_operands = []

        for dst_operand in dst_operands:
            if _type(dst_operand) == 'REG':
                pkts.append(self.makePrologueFUCrossbarPackets(instruction))
        return pkts
    
    def makePhiConstProloguePackets(self, instruction):
        print(f"Making phi const prologue packets for instruction {instruction}")
        for operation in instruction['operations']:
            if operation['opcode'] == 'PHI_CONST':
                phi_const_operation = operation
                break
        if phi_const_operation is None:
            raise ValueError("No PHI_CONST operation found")
        try:
            src_operands = phi_const_operation['src_operands']
        except Exception as e:
            src_operands = []
            
        pkts = []
        
        for src_operand in src_operands:
            if _type(src_operand) == 'PORT':
                if src_operand['operand'] == 'NORTH':
                    routing_xbar_idx = 0
                elif src_operand['operand'] == 'SOUTH':
                    routing_xbar_idx = 1
                elif src_operand['operand'] == 'WEST':
                    routing_xbar_idx = 2
                elif src_operand['operand'] == 'EAST':
                    routing_xbar_idx = 3
                pkts.append(self.makePrologueRoutingCrossbarPackets(instruction, routing_xbar_idx))
                
        print(f"Phi const prologue packets: {pkts}")
        return pkts
    
    
    def makePrologueFUPackets(self, instruction):
        return self.IntraCgraPktType(0, self.id_, 
                                     payload = self.CgraPayloadType(self.CMD_CONFIG_PROLOGUE_FU_, ctrl_addr = instruction['timestep'] % self.ii,
                                                                     data = self.DataType(1, 1)))
    def makePrologueRoutingCrossbarPackets(self, instruction, routing_xbar_idx):
        return self.IntraCgraPktType(0, self.id_, 
                                     payload = self.CgraPayloadType(self.CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_, ctrl_addr = instruction['timestep'] % self.ii,
                                                                     ctrl = self.CtrlType(fu_xbar_outport = [self.TileInType(routing_xbar_idx)] + [self.TileInType(0)] * 7),
                                                                     data = self.DataType(1, 1)))
    def makePrologueFUCrossbarPackets(self, instruction):
        return self.IntraCgraPktType(0, self.id_, 
                                     payload = self.CgraPayloadType(self.CMD_CONFIG_PROLOGUE_FU_CROSSBAR_, ctrl_addr = instruction['timestep'] % self.ii,
                                                                     ctrl = self.CtrlType(fu_xbar_outport = [self.FuOutType(0)] * 8),
                                                                     data = self.DataType(1, 1)))
    def makeTileSignals(self):
        consts = []
        all_signals = []
        all_instruction_signals = []
        prologue_signals = []
        
        # build all the instruction signals and get all the const
        for instruction in self.instructions:
            if instruction['timestep'] >= self.ii:
                prologue_signals.extend(self.makeProloguePackets(instruction))
            
            has_phi_const = False # cope with special PHI_CONST operation
            for operation in instruction['operations']:
                if operation['opcode'] == 'PHI_CONST':
                    has_phi_const = True
                    break
            if has_phi_const:
                prologue_signals.extend(self.makePhiConstProloguePackets(instruction))
            
            instruction_signals = InstructionSignals(
                id_ = self.id_,
                operations = instruction['operations'],
                opcode_in_EIR = instruction['operations'][0]['opcode'], # transient TODO: make it general
                ctrl_addr = instruction['timestep'],
                IntraCgraPktType = self.IntraCgraPktType,
                CgraPayloadType = self.CgraPayloadType,
                TileInType = self.TileInType,
                FuOutType = self.FuOutType,
                CMD_CONFIG_input = self.CMD_CONFIG_,
                CtrlType = self.CtrlType,
                FuInType = self.FuInType,
                B1Type = self.B1Type,
                B2Type = self.B2Type)
            all_instruction_signals.append(instruction_signals)
            
            const = instruction_signals.buildCtrlPkt()
            if const is not None:
                consts.extend(const)
        
        # make the const signals
        for idx, const_operand in enumerate(consts):
            const_pkt = self.IntraCgraPktType(0, self.id_, 
                                              payload = self.CgraPayloadType(self.CMD_CONST_,
                                                                             data = self.DataType(int(const_operand['operand']), 1)))
            all_signals.append(const_pkt)
            
        # make the pre-configuration
        ii_pkt = self.IntraCgraPktType(0, self.id_, 
                                       payload = self.CgraPayloadType(self.CMD_CONFIG_COUNT_PER_ITER_,
                                                                      data = self.DataType(self.ii, 1)))
        all_signals.append(ii_pkt)
        loop_times_pkt = self.IntraCgraPktType(0, self.id_, 
                                               payload = self.CgraPayloadType(self.CMD_CONFIG_TOTAL_CTRL_COUNT_,
                                                                              data = self.DataType(self.loop_times, 1)))
        all_signals.append(loop_times_pkt)
        
        # make the main packets
        for instruction_signals in all_instruction_signals:
            pkt = instruction_signals.makeCtrlPkt()
            all_signals.append(pkt)
            
        # make prologue packets
        # re-order the prologue packets 
        '''
        ordered_prologue_signals = []
        for pkt in prologue_signals:
            if pkt.cmd == self.CMD_CONFIG_PROLOGUE_FU_:
                ordered_prologue_signals.append(pkt)
        for pkt in prologue_signals:
            if pkt.cmd == self.CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_:
                ordered_prologue_signals.append(pkt)
        for pkt in prologue_signals:
            if pkt.cmd == self.CMD_CONFIG_PROLOGUE_FU_CROSSBAR_:
                ordered_prologue_signals.append(pkt)
                
        all_signals.extend(ordered_prologue_signals)
        '''
        all_signals.extend(prologue_signals)
        # make the launch packet
        launch_pkt = self.IntraCgraPktType(0, self.id_, 
                                           payload = self.CgraPayloadType(self.CMD_LAUNCH_))
        all_signals.append(launch_pkt)
        
        return all_signals
class ScriptFactory:
    FromFu = 0
    FromRouting = 1
    
    def __init__(self, 
                 path, 
                 CtrlType, 
                 IntraCgraPktType, 
                 CgraPayloadType, 
                 TileInType, 
                 FuOutType, 
                 CMD_CONFIG_input, 
                 FuInType, 
                 ii,
                 loop_times,
                 CMD_CONST_input,
                 CMD_CONFIG_COUNT_PER_ITER_input,
                 CMD_CONFIG_TOTAL_CTRL_COUNT_input,
                 CMD_CONFIG_PROLOGUE_FU_input,
                 CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input,
                 CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input,
                 CMD_LAUNCH_input,
                 DataType,
                 B1Type,
                 B2Type):
        self.yaml_struct = yaml.load(open(path, 'r'), Loader=yaml.FullLoader)
        self.path = path
        self.CtrlType = CtrlType
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.CMD_CONFIG_ = CMD_CONFIG_input
        self.FuInType = FuInType
        self.ii = ii
        self.loop_times = loop_times
        self.CMD_CONST_ = CMD_CONST_input
        self.CMD_CONFIG_COUNT_PER_ITER_ = CMD_CONFIG_COUNT_PER_ITER_input
        self.CMD_CONFIG_TOTAL_CTRL_COUNT_ = CMD_CONFIG_TOTAL_CTRL_COUNT_input
        self.CMD_CONFIG_PROLOGUE_FU_ = CMD_CONFIG_PROLOGUE_FU_input
        self.CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_ = CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input
        self.CMD_CONFIG_PROLOGUE_FU_CROSSBAR_ = CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input
        self.CMD_LAUNCH_ = CMD_LAUNCH_input
        self.DataType = DataType
        self.B1Type = B1Type
        self.B2Type = B2Type
    
    def makeVectorCGRAPkts(self):
        
        pkts = {}
        cores = self.yaml_struct['array_config']['cores']
        
        
        for core in cores:
            x, y = core['column'], core['row']
            entry = core['entries'][0]
            instructions = entry['instructions']
            id_ = core['core_id']
            
            tile_signals = TileSignals(
                CtrlType = self.CtrlType,
                IntraCgraPktType = self.IntraCgraPktType,
                CgraPayloadType = self.CgraPayloadType,
                TileInType = self.TileInType,
                FuOutType = self.FuOutType,
                CMD_CONFIG_input = self.CMD_CONFIG_,
                FuInType = self.FuInType,
                id_ = id_,
                loop_times = self.loop_times, 
                ii = self.ii, 
                instructions = instructions,
                CMD_CONST_input = self.CMD_CONST_,
                CMD_CONFIG_COUNT_PER_ITER_input = self.CMD_CONFIG_COUNT_PER_ITER_,
                CMD_CONFIG_TOTAL_CTRL_COUNT_input = self.CMD_CONFIG_TOTAL_CTRL_COUNT_,
                CMD_CONFIG_PROLOGUE_FU_input = self.CMD_CONFIG_PROLOGUE_FU_,
                CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input = self.CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_,
                CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input = self.CMD_CONFIG_PROLOGUE_FU_CROSSBAR_,
                CMD_LAUNCH_input = self.CMD_LAUNCH_,
                DataType = self.DataType,
                B1Type = self.B1Type,
                B2Type = self.B2Type,
                )
            tile_signals = tile_signals.makeTileSignals()
            pkts[(x, y)] = tile_signals
            
        return pkts
    
from validation.test.dummy import *
    
if __name__ == "__main__":
    print("Test the Basic Functionality of the ScriptFactory")

    script_factory = ScriptFactory(
        path = "./validation/test/fir_acceptance_test.yaml",
        CtrlType = CtrlTypeDummy,
        IntraCgraPktType = IntraCgraPktTypeDummy,
        CgraPayloadType = CgraPayloadTypeDummy,
        TileInType = TileInTypeDummy,
        FuOutType = FuOutTypeDummy,
        CMD_CONFIG_input = CMD_CONFIG_Dummy(),
        FuInType = FuInTypeDummy,
        ii = 4,
        loop_times = 2,
        CMD_CONST_input = CMD_CONST_Dummy(),
        CMD_CONFIG_COUNT_PER_ITER_input = CMD_CONFIG_COUNT_PER_ITER_Dummy(),
        CMD_CONFIG_TOTAL_CTRL_COUNT_input = CMD_CONFIG_TOTAL_CTRL_COUNT_Dummy(),
        CMD_CONFIG_PROLOGUE_FU_input = CMD_CONFIG_PROLOGUE_FU_Dummy(),
        CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_input = CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_Dummy(),
        CMD_CONFIG_PROLOGUE_FU_CROSSBAR_input = CMD_CONFIG_PROLOGUE_FU_CROSSBAR_Dummy(),
        CMD_LAUNCH_input = CMD_LAUNCH_Dummy(),
        DataType = DataTypeDummy,
        B1Type = B1TypeDummy,
        B2Type = B2TypeDummy,
    )
    
    pkts = script_factory.makeVectorCGRAPkts()
    for x, y in pkts:
        print(f"Tile ({x}, {y}):")
        for pkt in pkts[(x, y)]:
            print(pkt)
            print("--------------------------------")
    