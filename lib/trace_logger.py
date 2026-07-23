"""
=========================================================================
trace_logger.py
=========================================================================
Structured JSONL trace logger for CGRA visualization.

Captures per-cycle state of the CGRA including tile data, control signals,
FU operations, crossbar routing, memory accesses, and controller state.

Author : Auto-generated for visualization support
  Date : 2026
"""

import json
import os
from .opt_type import OPT_SYMBOL_DICT


class CgraTraceLogger:
  """Logs CGRA state per cycle as JSONL for visualization."""

  def __init__(self, filepath, width, height, topology, cgra_id=0):
    self.filepath = filepath
    self.width = width
    self.height = height
    self.topology = topology
    self.cgra_id = cgra_id
    self.cycle = 0
    self._file = None

  def open(self):
    os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
    self._file = open(self.filepath, 'w')

  def close(self):
    if self._file:
      self._file.close()
      self._file = None

  def _safe_int(self, val):
    """Convert pymtl3 Bits to int safely."""
    try:
      return int(val)
    except:
      return 0

  def _extract_data_msg(self, ifc):
    """Extract DataType message fields."""
    try:
      return {
        "payload": self._safe_int(ifc.msg.payload),
        "predicate": self._safe_int(ifc.msg.predicate),
        "val": self._safe_int(ifc.val),
        "rdy": self._safe_int(ifc.rdy),
      }
    except:
      return {"payload": 0, "predicate": 0, "val": 0, "rdy": 0}

  def _extract_tile(self, tile, tile_idx):
    """Extract all relevant signals from a single tile."""
    w = self.width
    row = tile_idx // w
    col = tile_idx % w

    # recv_data / send_data ports
    recv_data = []
    for i, rd in enumerate(tile.recv_data):
      recv_data.append(self._extract_data_msg(rd))

    send_data = []
    for i, sd in enumerate(tile.send_data):
      send_data.append(self._extract_data_msg(sd))

    # FU (element) info
    fu_inputs = []
    for inp in tile.element.recv_in:
      fu_inputs.append(self._extract_data_msg(inp))

    fu_outputs = []
    for out in tile.element.send_out:
      fu_outputs.append(self._extract_data_msg(out))

    operation_code = self._safe_int(tile.ctrl_mem.send_ctrl.msg.operation)
    operation_symbol = OPT_SYMBOL_DICT.get(
        tile.ctrl_mem.send_ctrl.msg.operation, f"op{operation_code}")

    fu_const = self._extract_data_msg(tile.element.recv_const)

    # Crossbar routing config
    num_routing_outports = len(tile.routing_crossbar.crossbar_outport)
    routing_xbar_config = []
    for i in range(num_routing_outports):
      routing_xbar_config.append(self._safe_int(
          tile.routing_crossbar.crossbar_outport[i]))

    fu_xbar_config = []
    for i in range(len(tile.fu_crossbar.crossbar_outport)):
      fu_xbar_config.append(self._safe_int(
          tile.fu_crossbar.crossbar_outport[i]))

    # Ctrl mem state
    ctrl_addr = self._safe_int(tile.ctrl_mem.reg_file.raddr[0])
    ctrl_times = self._safe_int(tile.ctrl_mem.times)
    ctrl_total_steps = self._safe_int(tile.ctrl_mem.total_ctrl_steps_val)
    ctrl_started = self._safe_int(tile.ctrl_mem.start_iterate_ctrl)
    ctrl_complete = self._safe_int(tile.ctrl_mem.sent_complete)
    ctrl_val = self._safe_int(tile.ctrl_mem.send_ctrl.val)
    ctrl_rdy = self._safe_int(tile.ctrl_mem.send_ctrl.rdy)

    # Prologue state
    prologue_fu_count = self._safe_int(tile.ctrl_mem.prologue_count_outport_fu)
    try:
      prologue_routing_xbar = self._safe_int(tile.routing_crossbar.prologue_allowing_vector)
    except:
      prologue_routing_xbar = 0
    try:
      prologue_fu_xbar = self._safe_int(tile.fu_crossbar.prologue_allowing_vector)
    except:
      prologue_fu_xbar = 0

    # Done flags
    element_done = self._safe_int(tile.element_done)
    fu_xbar_done = self._safe_int(tile.fu_crossbar_done)
    routing_xbar_done = self._safe_int(tile.routing_crossbar_done)

    # Memory access
    mem_raddr = self._extract_data_msg(tile.to_mem_raddr) if hasattr(tile.to_mem_raddr, 'val') else None
    mem_waddr = self._extract_data_msg(tile.to_mem_waddr) if hasattr(tile.to_mem_waddr, 'val') else None
    mem_rdata = self._extract_data_msg(tile.from_mem_rdata) if hasattr(tile.from_mem_rdata, 'val') else None
    mem_wdata = self._extract_data_msg(tile.to_mem_wdata) if hasattr(tile.to_mem_wdata, 'val') else None

    # Routing crossbar recv/send data
    routing_xbar_recv = []
    for rd in tile.routing_crossbar.recv_data:
      routing_xbar_recv.append(self._extract_data_msg(rd))

    routing_xbar_send = []
    for sd in tile.routing_crossbar.send_data:
      routing_xbar_send.append(self._extract_data_msg(sd))

    fu_xbar_recv = []
    for rd in tile.fu_crossbar.recv_data:
      fu_xbar_recv.append(self._extract_data_msg(rd))

    fu_xbar_send = []
    for sd in tile.fu_crossbar.send_data:
      fu_xbar_send.append(self._extract_data_msg(sd))

    # Controller packet interface on tile
    ctrl_pkt_recv_val = self._safe_int(tile.recv_from_controller_pkt.val)
    ctrl_pkt_recv_rdy = self._safe_int(tile.recv_from_controller_pkt.rdy)
    ctrl_pkt_send_val = self._safe_int(tile.send_to_controller_pkt.val)
    ctrl_pkt_send_rdy = self._safe_int(tile.send_to_controller_pkt.rdy)

    try:
      ctrl_pkt_recv_cmd = self._safe_int(
          tile.recv_from_controller_pkt.msg.payload.cmd)
    except:
      ctrl_pkt_recv_cmd = 0

    return {
      "id": tile_idx,
      "row": row,
      "col": col,
      "recv_data": recv_data,
      "send_data": send_data,
      "fu": {
        "operation": operation_code,
        "operation_symbol": operation_symbol,
        "inputs": fu_inputs,
        "outputs": fu_outputs,
        "const": fu_const,
        "recv_opt_val": self._safe_int(tile.element.recv_opt.val),
        "recv_opt_rdy": self._safe_int(tile.element.recv_opt.rdy),
      },
      "routing_xbar": {
        "config": routing_xbar_config,
        "recv": routing_xbar_recv,
        "send": routing_xbar_send,
      },
      "fu_xbar": {
        "config": fu_xbar_config,
        "recv": fu_xbar_recv,
        "send": fu_xbar_send,
      },
      "ctrl_mem": {
        "addr": ctrl_addr,
        "times": ctrl_times,
        "total_steps": ctrl_total_steps,
        "started": ctrl_started,
        "complete": ctrl_complete,
        "ctrl_val": ctrl_val,
        "ctrl_rdy": ctrl_rdy,
      },
      "done_flags": {
        "element": element_done,
        "fu_xbar": fu_xbar_done,
        "routing_xbar": routing_xbar_done,
      },
      "prologue": {
        "fu_count": prologue_fu_count,
        "routing_xbar": prologue_routing_xbar,
        "fu_xbar": prologue_fu_xbar,
      },
      "mem_access": {
        "raddr": mem_raddr,
        "rdata": mem_rdata,
        "waddr": mem_waddr,
        "wdata": mem_wdata,
      },
      "ctrl_pkt": {
        "recv_val": ctrl_pkt_recv_val,
        "recv_rdy": ctrl_pkt_recv_rdy,
        "recv_cmd": ctrl_pkt_recv_cmd,
        "send_val": ctrl_pkt_send_val,
        "send_rdy": ctrl_pkt_send_rdy,
      },
    }

  def _extract_controller(self, controller):
    """Extract controller state."""
    try:
      cpu_recv_val = self._safe_int(controller.recv_from_cpu_pkt.val)
      cpu_recv_rdy = self._safe_int(controller.recv_from_cpu_pkt.rdy)
      cpu_send_val = self._safe_int(controller.send_to_cpu_pkt.val)
      cpu_send_rdy = self._safe_int(controller.send_to_cpu_pkt.rdy)

      ring_send_val = self._safe_int(controller.send_to_ctrl_ring_pkt.val)
      ring_send_rdy = self._safe_int(controller.send_to_ctrl_ring_pkt.rdy)
      ring_recv_val = self._safe_int(controller.recv_from_ctrl_ring_pkt.val)
      ring_recv_rdy = self._safe_int(controller.recv_from_ctrl_ring_pkt.rdy)

      try:
        cpu_recv_cmd = self._safe_int(
            controller.recv_from_cpu_pkt.msg.payload.cmd)
      except:
        cpu_recv_cmd = 0

      try:
        ring_recv_cmd = self._safe_int(
            controller.recv_from_ctrl_ring_pkt.msg.payload.cmd)
      except:
        ring_recv_cmd = 0

      return {
        "cpu_recv": {"val": cpu_recv_val, "rdy": cpu_recv_rdy,
                     "cmd": cpu_recv_cmd},
        "cpu_send": {"val": cpu_send_val, "rdy": cpu_send_rdy},
        "ring_send": {"val": ring_send_val, "rdy": ring_send_rdy},
        "ring_recv": {"val": ring_recv_val, "rdy": ring_recv_rdy,
                      "cmd": ring_recv_cmd},
      }
    except:
      return {}

  def _extract_data_mem(self, data_mem):
    """Extract data memory state."""
    try:
      # Read/write from tiles
      tile_reads = []
      for i in range(data_mem.num_rd_tiles):
        tile_reads.append({
          "addr": self._extract_data_msg(data_mem.recv_raddr[i]),
          "data": self._extract_data_msg(data_mem.send_rdata[i]),
        })

      tile_writes = []
      for i in range(data_mem.num_wr_tiles):
        tile_writes.append({
          "addr": self._extract_data_msg(data_mem.recv_waddr[i]),
          "data": self._extract_data_msg(data_mem.recv_wdata[i]),
        })

      # Memory bank contents (first few entries)
      banks = []
      for b in range(data_mem.num_banks_per_cgra):
        bank_data = []
        mem_wrapper = data_mem.memory_wrapper[b]
        try:
          for addr_idx in range(min(16, len(mem_wrapper.data_mem.regs))):
            val = self._safe_int(mem_wrapper.data_mem.regs[addr_idx])
            if val != 0:
              bank_data.append({"addr": addr_idx, "val": val})
        except:
          pass
        banks.append(bank_data)

      return {
        "tile_reads": tile_reads,
        "tile_writes": tile_writes,
        "banks": banks,
      }
    except:
      return {}

  def log_cycle(self, cgra):
    """Log the full CGRA state for the current cycle."""
    if not self._file:
      return

    tiles = []
    for i, tile in enumerate(cgra.tile):
      tiles.append(self._extract_tile(tile, i))

    record = {
      "cycle": self.cycle,
      "cgra_id": self._safe_int(cgra.cgra_id),
      "width": self.width,
      "height": self.height,
      "topology": self.topology,
      "tiles": tiles,
      "controller": self._extract_controller(cgra.controller),
      "data_mem": self._extract_data_mem(cgra.data_mem),
    }

    self._file.write(json.dumps(record) + '\n')
    self.cycle += 1

  def __enter__(self):
    self.open()
    return self

  def __exit__(self, *args):
    self.close()


# Global logger instance for easy access
_global_logger = None


def init_trace_logger(filepath, width, height, topology, cgra_id=0):
  """Initialize the global trace logger."""
  global _global_logger
  if _global_logger:
    _global_logger.close()
  _global_logger = CgraTraceLogger(filepath, width, height, topology, cgra_id)
  _global_logger.open()
  return _global_logger


def get_trace_logger():
  """Get the global trace logger instance."""
  return _global_logger


def close_trace_logger():
  """Close the global trace logger."""
  global _global_logger
  if _global_logger:
    _global_logger.close()
    _global_logger = None
