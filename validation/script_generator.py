import sys
from antlr4 import *
from EasyCGRALexer import EasyCGRALexer
from EasyCGRAParser import EasyCGRAParser
from RealEasyCGRAParserVisitor import RealEasyCGRAParserVisitor


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




class VectorCGRApkt:

    def __init__(self, program_in_YAML, CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, OpCode, fuInCode, id_):
        # load the program in YAML
        
        
        
        self.IntraCgraPktType = IntraCgraPktType
        self.CgraPayloadType = CgraPayloadType
        self.TileInType = TileInType
        self.FuOutType = FuOutType
        self.TileInParams = [0, 0, 0, 0, 0, 0, 0, 0]
        self.FuOutParams = [0, 0, 0, 0, 0, 0, 0, 0]
        self.config = config
        self.OpCode = OpCode
        self.fuInCode = fuInCode
        self.id_ = id_
        self.CtrlType = CtrlType
        
    def makeCtrlPkt(self):
        TileIn = [ self.TileInType(self.TileInParams[idx]) for idx in range(8) ]
        FuOut = [ self.FuOutType(self.FuOutParams[idx]) for idx in range(8) ]
        ctrl = self.CtrlType(self.OpCode, 0, self.fuInCode, TileIn, FuOut)
        payload = self.CgraPayloadType(self.config, ctrl_addr = 0, ctrl = ctrl)
        pkt = self.IntraCgraPktType(0, self.id_, payload)
        return pkt

    
class ScriptFactory:
    FromFu = 0
    FromRouting = 1
    def makeVectorCGRAPkts(ScriptInsts, CtrlType,IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, fuInCode, id_, FromFuOrRouting = FromRouting): #False means from routing inst
        pkts = []
        for cInst in ScriptInsts:
            #print("cInst: ", cInst)
            pkt = VectorCGRApkt(CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, None, fuInCode, id_)
            # find opcode
            for inst in cInst:
                if inst.opCode != EasyCGRAParser.MOV: # not the routing inst
                    pkt.OpCode = EasyToVectorOpcodeMap.opMap[inst.opCode]
            
            if pkt.OpCode is None:
                pkt.OpCode = ... # TODO: alter this with your pure routing inst's opCode
            # update the params
            for inst in cInst:
                if inst.opCode != EasyCGRAParser.MOV:
                    # cope with the srcOperands
                    if FromFuOrRouting == ScriptFactory.FromRouting:
                        #print("inst.srcOperands: ", inst.srcOperands)
                        for idx in range(len(inst.srcOperands)):
                            if len(inst.srcOperands[idx].IDs) == 0:
                                continue
                            if inst.srcOperands[idx].IDs[-1] == "NORTH": 
                                pkt.TileInParams[idx + 4] = 1
                            elif inst.srcOperands[idx].IDs[-1] == "SOUTH": 
                                pkt.TileInParams[idx + 4] = 2
                            elif inst.srcOperands[idx].IDs[-1] == "WEST":
                                pkt.TileInParams[idx + 4] = 3
                            elif inst.srcOperands[idx].IDs[-1] == "EAST":
                                pkt.TileInParams[idx + 4] = 4
                    elif FromFuOrRouting == ScriptFactory.FromFu:
                        for idx in range(len(inst.srcOperands)):
                            ... 
                        
                    
                    # TODO: only one dstOperand?
                    if inst.dstOperands[0].IDs[-1] == "NORTH":
                        pkt.FuOutParams[0] = 1
                    elif inst.dstOperands[0].IDs[-1] == "SOUTH":
                        pkt.FuOutParams[1] = 1
                    elif inst.dstOperands[0].IDs[-1] == "WEST":
                        pkt.FuOutParams[2] = 1
                    elif inst.dstOperands[0].IDs[-1] == "EAST":
                        pkt.FuOutParams[3] = 1
                    elif inst.dstOperands[0].IDs[-1] == "$0":
                        pkt.FuOutParams[4] = 1
                    elif inst.dstOperands[0].IDs[-1] == "$1":
                        pkt.FuOutParams[5] = 1
                    elif inst.dstOperands[0].IDs[-1] == "$2":
                        pkt.FuOutParams[6] = 1
                    elif inst.dstOperands[0].IDs[-1] == "$3":
                        pkt.FuOutParams[7] = 1
                        
        
                else: # the routing inst
                    src_route = inst.srcOperands[0].IDs[-1]
                    dst_route = inst.dstOperands[0].IDs[-1]
                    if src_route == "NORTH":
                        src_route_idx = 1
                    elif src_route == "SOUTH":
                        src_route_idx = 2
                    elif src_route == "WEST":
                        src_route_idx = 3
                    elif src_route == "EAST":
                        src_route_idx = 4
                    if dst_route == "NORTH":
                        dst_route_idx = 0
                    elif dst_route == "SOUTH":
                        dst_route_idx = 1
                    elif dst_route == "WEST":
                        dst_route_idx = 2
                    elif dst_route == "EAST":
                        dst_route_idx = 3
                        
                    pkt.TileInParams[dst_route_idx] = src_route_idx
            pkts.append(pkt.makeCtrlPkt())
            
        return pkts
    
                    
    
    @classmethod
    def make(cls, file, CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, fuInCode, id_, FromFuOrRouting = FromRouting):
        input_stream = FileStream(file)
        lexer = EasyCGRALexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = EasyCGRAParser(stream)
        tree = parser.compilationUnit()
        #print(type(tree))
        if parser.getNumberOfSyntaxErrors() > 0:
            print(f"Syntax errors in your script {file}.")
            return None
        else:
            vinterp = RealEasyCGRAParserVisitor()
            #print("Tree: ", tree)
            insts = vinterp.visitCompilationUnit(tree)
            #insts = vinterp.visitCompilationUnit(tree)
            #print("Insts: ", insts)
            pkts = ScriptFactory.makeVectorCGRAPkts(insts, CtrlType, IntraCgraPktType, CgraPayloadType, TileInType, FuOutType, config, fuInCode, id_, FromFuOrRouting)
            #print("Pkts: ", pkts)
            return pkts
        