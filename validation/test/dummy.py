class CgraPayloadTypeDummy:
    def __init__(self, config, ctrl_addr=None, ctrl = None, data=None):
        self.config = config
        self.ctrl_addr = ctrl_addr
        self.ctrl = ctrl
        self.data = data
        
    def __str__(self):
        ctrl_addr_str = f"ctrl_addr = {self.ctrl_addr},\n" if self.ctrl_addr is not None else ""
        ctrl_str = f"ctrl = {self.ctrl},\n" if self.ctrl is not None else ""
        data_str = f"data = {self.data})" if self.data is not None else ")"
        return f"CgraPayloadType({self.config}, {ctrl_addr_str} {ctrl_str} {data_str})"


class IntraCgraPktTypeDummy:
    def __init__(self, first, second, payload):
        self.first = first
        self.second = second
        self.payload = payload
        
    def __str__(self):
        return f"IntraCgraPktType({self.first}, {self.second},\n payload = {self.payload})"

class CtrlTypeDummy:
    def __init__(self, op_code = None, fu_in_code = None, tile_in = None, fu_out = None, write_reg_from = None, write_reg_idx = None, read_reg_from = None, read_reg_idx = None, routing_xbar_outport = None, fu_xbar_outport = None):
        self.op_code = op_code
        self.fu_in_code = fu_in_code
        self.tile_in = tile_in
        self.fu_out = fu_out
        self.write_reg_from = write_reg_from
        self.write_reg_idx = write_reg_idx
        self.read_reg_from = read_reg_from
        self.read_reg_idx = read_reg_idx
        self.routing_xbar_outport = routing_xbar_outport
        self.fu_xbar_outport = fu_xbar_outport
    

        
    def __str__(self):
        if self.op_code is not None:
            op_code_str = f"{self.op_code},\n"
        else:
            op_code_str = ""
        if self.fu_in_code is not None:
            fu_in_code_str = f"[{', '.join(str(f) for f in self.fu_in_code)}],\n"
        else:
            fu_in_code_str = ""
        if self.tile_in is not None:
            tile_in_str_line0 = f"[{', '.join(str(t) for t in self.tile_in[0:4])}, \n"
            tile_in_str_line1 = f"{', '.join(str(t) for t in self.tile_in[4:8])}], \n"
        else:
            tile_in_str_line0 = ""
            tile_in_str_line1 = ""
        if self.fu_out is not None:
            fu_out_str_line0 = f"[{', '.join(str(f) for f in self.fu_out[0:4])}, \n"
            fu_out_str_line1 = f"{', '.join(str(f) for f in self.fu_out[4:8])}], \n"
        else:
            fu_out_str_line0 = ""
            fu_out_str_line1 = ""
        if self.write_reg_from is not None:
            write_reg_from_str = f"write_reg_from = [{', '.join(str(w) for w in self.write_reg_from)}], \n"
        else:
            write_reg_from_str = ""
        if self.write_reg_idx is not None:
            write_reg_idx_str = f"write_reg_idx = [{', '.join(str(w) for w in self.write_reg_idx)}], \n"
        else:
            write_reg_idx_str = ""
        if self.read_reg_from is not None:
            read_reg_from_str = f"read_reg_from = [{', '.join(str(r) for r in self.read_reg_from)}], \n"
        else:
            read_reg_from_str = ""
        if self.read_reg_idx is not None:
            read_reg_idx_str = f"read_reg_idx = [{', '.join(str(r) for r in self.read_reg_idx)}], \n"
        else:
            read_reg_idx_str = ""
        
        if self.routing_xbar_outport is not None:
            routing_xbar_outport_str = f"routing_xbar_outport = [{', '.join(str(r) for r in self.routing_xbar_outport)}], \n"
        else:
            routing_xbar_outport_str = ""
        if self.fu_xbar_outport is not None:
            fu_xbar_outport_str = f"fu_xbar_outport = [{', '.join(str(f) for f in self.fu_xbar_outport)}], \n"
        else:
            fu_xbar_outport_str = ""
        return f"CtrlType({op_code_str} {fu_in_code_str} {tile_in_str_line0} {tile_in_str_line1} {fu_out_str_line0} {fu_out_str_line1} {write_reg_from_str} {write_reg_idx_str} {read_reg_from_str} {read_reg_idx_str} {routing_xbar_outport_str} {fu_xbar_outport_str})"

            
class TileInTypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"TileInType({self.params})"
    
class FuOutTypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"FuOutType({self.params})"

class FuInTypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"FuInType({self.params})"

class CMD_CONFIG_PROLOGUE_FU_Dummy:
    def __str__(self):
        return "CMD_CONFIG_PROLOGUE_FU"
    
class CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR_Dummy:
    def __str__(self):
        return "CMD_CONFIG_PROLOGUE_ROUTING_CROSSBAR"
    
class CMD_CONFIG_PROLOGUE_FU_CROSSBAR_Dummy:
    def __str__(self):
        return "CMD_CONFIG_PROLOGUE_FU_CROSSBAR"
    
class CMD_LAUNCH_Dummy:
    def __str__(self):
        return "CMD_LAUNCH"
    
class CMD_CONFIG_Dummy:
    def __str__(self):
        return "CMD_CONFIG"
    
class CMD_CONST_Dummy:
    def __str__(self):
        return "CMD_CONST"
    
class CMD_CONFIG_COUNT_PER_ITER_Dummy:
    def __str__(self):
        return "CMD_CONFIG_COUNT_PER_ITER"
    
class CMD_CONFIG_TOTAL_CTRL_COUNT_Dummy:
    def __str__(self):
        return "CMD_CONFIG_TOTAL_CTRL_COUNT"


class DataTypeDummy:
    def __init__(self, param1, param2):
        self.param1 = param1
        self.param2 = param2
        
    def __str__(self):
        return f"DataType({self.param1}, {self.param2})"
    
class B1TypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"b1({self.params})"
    
class B2TypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"b2({self.params})"
    
class RegIdxTypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"{self.params}"
    
class CtrlAddrTypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"{self.params}"
    
class DataAddrTypeDummy:
    def __init__(self, params):
        self.params = params
        
    def __str__(self):
        return f"{self.params}"