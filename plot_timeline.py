#!/usr/bin/env python3
"""
==========================================================================
plot_timeline.py
==========================================================================
Visualize CGRA execution timeline from JSONL trace files.

For each cycle and each active tile, shows:
  - Executing: the FU operation (green)
  - Stalled waiting for upstream (input not ready): orange
  - Stalled waiting for downstream (output backpressure): red
  - Idle / NAH: light gray

Usage:
  python plot_timeline.py <trace.jsonl> [--start CYCLE] [--end CYCLE] [--out FILE]

Author : Auto-generated
  Date : 2026
"""

import argparse
import json
import sys
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import to_rgba

# ── Mesh port conventions ──────────────────────────────────────────────
# PORT_INDEX: 0=North 1=South 2=West 3=East
PORT_NAMES = ['N', 'S', 'W', 'E']

def neighbor_id(tile_id, port_idx, width, height):
    """Return neighbor tile id for the given port, or None if boundary.

    Coordinate system: origin at bottom-left, col grows right, row grows up.
    tile_id = col + row * width.  North = row+1, South = row-1.
    """
    col = tile_id % width
    row = tile_id // width
    if port_idx == 0:  # North → row+1
        return tile_id + width if row < height - 1 else None
    elif port_idx == 1:  # South → row-1
        return tile_id - width if row > 0 else None
    elif port_idx == 2:  # West → col-1
        return tile_id - 1 if col > 0 else None
    elif port_idx == 3:  # East → col+1
        return tile_id + 1 if col < width - 1 else None
    return None


# ── Classify tile state per cycle ──────────────────────────────────────
# States
S_IDLE       = 'idle'
S_EXEC       = 'exec'
S_ROUTING    = 'routing'          # DATA_MOV: routing crossbar forwarding
S_WAIT_UP    = 'wait_upstream'    # FU has opt but input not valid yet
S_WAIT_DOWN  = 'wait_downstream'  # FU output valid but downstream not ready

def _classify_routing(tile, width, height):
    """Classify a tile whose FU is NAH but may be doing routing work.

    A tile is considered to be routing only when its routing_xbar config
    has a non-zero entry on a tile port (N/S/W/E, indices 0-3).  This
    means the current control step explicitly programs tile-to-tile data
    forwarding.  Data arriving on the crossbar without a matching config
    entry is just early-arriving data sitting in a buffer — not an active
    routing operation.
    """
    tid = tile['id']
    rx = tile['routing_xbar']
    rx_recv = rx['recv']
    rx_send = rx['send']
    config = rx['config']
    num_tile_ports = min(4, len(rx_send))  # N/S/W/E

    # Only consider this tile as routing if the config programs at least
    # one tile output port (first 4 entries) to forward from some input.
    has_route_config = any(config[i] != 0 for i in range(num_tile_ports))

    if not has_route_config:
        return S_IDLE, '', ''

    # Config says this cycle should route.  Now check data flow status.

    # Check for downstream stall: send has val=1 but rdy=0.
    blocked_sends = []
    for idx in range(num_tile_ports):
        if config[idx] == 0:
            continue
        s = rx_send[idx]
        if s['val'] and not s['rdy']:
            nb = neighbor_id(tid, idx, width, height)
            blocked_sends.append((idx, nb))

    if blocked_sends:
        targets = []
        for idx, nb in blocked_sends:
            if nb is not None:
                targets.append(f't{nb}({PORT_NAMES[idx]})')
            else:
                targets.append(f'bnd({PORT_NAMES[idx]})')
        return S_WAIT_DOWN, 'route', ','.join(targets)

    # Check for upstream stall: config expects data from a recv port
    # but that recv port has no valid data yet.
    waiting_recv = []
    for si in range(num_tile_ports):
        cfg_val = config[si]
        if cfg_val > 0:
            # cfg_val is 1-indexed recv port; recv_idx = cfg_val - 1
            ri = cfg_val - 1
            if ri < len(rx_recv) and not rx_recv[ri]['val']:
                nb = neighbor_id(tid, ri, width, height) if ri < 4 else None
                if nb is not None:
                    waiting_recv.append(f't{nb}({PORT_NAMES[ri]})')
                else:
                    waiting_recv.append(f'p{ri}')

    if waiting_recv:
        return S_WAIT_UP, 'route', ','.join(waiting_recv)

    # Data is flowing through successfully.
    return S_ROUTING, 'route', ''


def classify_tile(tile, width, height):
    """
    Return (state, op_symbol, annotation) for one tile in one cycle.

    state      : one of S_IDLE / S_EXEC / S_ROUTING / S_WAIT_UP / S_WAIT_DOWN
    op_symbol  : e.g. "(+)", "(ld)", "route"
    annotation : short text describing who is being waited on
    """
    fu = tile['fu']
    op = fu['operation_symbol']
    opt_val = fu['recv_opt_val']
    opt_rdy = fu['recv_opt_rdy']
    tid = tile['id']

    # NAH / not started → check if the tile is doing routing instead.
    if op in ('(start)', '(NAH)') or opt_val == 0:
        return _classify_routing(tile, width, height)

    inputs  = fu['inputs']
    outputs = fu['outputs']

    # Check if FU is executing (opt handshake fires: val & rdy both 1)
    if opt_val and opt_rdy:
        return S_EXEC, op, ''

    # opt_val=1 but opt_rdy=0 → stalled.
    # Determine whether stall is upstream (missing input) or downstream
    # (output backpressure).

    # Downstream stall: at least one output has val=1 but rdy=0.
    waiting_outputs = []
    for idx, out in enumerate(outputs):
        if out['val'] and not out['rdy']:
            waiting_outputs.append(idx)

    # Also check tile-level send_data (routing xbar → neighbor) for
    # downstream backpressure.
    send_data = tile.get('send_data', [])
    blocked_sends = []
    for idx, sd in enumerate(send_data):
        if sd['val'] and not sd['rdy']:
            nb = neighbor_id(tid, idx, width, height)
            blocked_sends.append((idx, nb))

    if waiting_outputs or blocked_sends:
        targets = []
        for idx, nb in blocked_sends:
            if nb is not None:
                targets.append(f't{nb}({PORT_NAMES[idx]})')
            else:
                targets.append(f'bnd({PORT_NAMES[idx]})')
        for idx in waiting_outputs:
            targets.append(f'out{idx}')
        ann = ','.join(targets) if targets else 'downstream'
        return S_WAIT_DOWN, op, ann

    # Upstream stall: FU is waiting for operands.
    # Use routing_xbar config to find which neighbor should supply data
    # to FU inports.  Config indices >= num_tile_ports are FU inports;
    # config value is 1-indexed recv port (0 = not connected).
    rx_cfg = tile['routing_xbar']['config']
    rx_recv = tile['routing_xbar']['recv']
    num_tile_ports = 4
    sources = []
    for fi, cfg_val in enumerate(rx_cfg):
        if fi < num_tile_ports or cfg_val == 0:
            continue
        # cfg_val is 1-indexed; recv port index = cfg_val - 1
        ri = cfg_val - 1
        if ri < len(rx_recv) and not rx_recv[ri]['val']:
            if ri < num_tile_ports:
                nb = neighbor_id(tid, ri, width, height)
                if nb is not None:
                    sources.append(f't{nb}({PORT_NAMES[ri]})')
                else:
                    sources.append(f'bnd({PORT_NAMES[ri]})')
            else:
                sources.append(f'p{ri}')

    # Also check recv_data for missing tile-level inputs.
    if not sources:
        recv_data = tile.get('recv_data', [])
        for idx, rd in enumerate(recv_data):
            if rd['rdy'] and not rd['val']:
                nb = neighbor_id(tid, idx, width, height)
                if nb is not None:
                    sources.append(f't{nb}({PORT_NAMES[idx]})')

    # Also check if const is waited on.
    if fu['const']['rdy'] and not fu['const']['val']:
        sources.append('const')

    ann = ','.join(sources) if sources else 'upstream'
    return S_WAIT_UP, op, ann


# ── Load trace ─────────────────────────────────────────────────────────

def load_trace(path, start_cycle=None, end_cycle=None):
    """Load JSONL trace, return list of cycle records."""
    records = []
    with open(path) as f:
        for line in f:
            rec = json.loads(line)
            c = rec['cycle']
            if start_cycle is not None and c < start_cycle:
                continue
            if end_cycle is not None and c > end_cycle:
                continue
            records.append(rec)
    return records


# ── Determine active tiles ─────────────────────────────────────────────

def find_active_tiles(records, width, height):
    """Return sorted list of tile ids that perform at least one non-idle op
    (including routing-only tiles whose crossbar forwards data)."""
    active = set()
    for rec in records:
        for tile in rec['tiles']:
            op = tile['fu']['operation_symbol']
            if op not in ('(start)', '(NAH)'):
                active.add(tile['id'])
            else:
                # Check if routing crossbar config programs any tile
                # port forwarding (not just data passing through).
                rx_cfg = tile['routing_xbar']['config']
                if any(rx_cfg[i] != 0 for i in range(min(4, len(rx_cfg)))):
                    active.add(tile['id'])
    return sorted(active)


# ── Build timeline matrix ──────────────────────────────────────────────

def build_timeline(records, active_tiles, width, height):
    """
    Return:
      cycles     : list of cycle numbers
      tile_ids   : list of active tile ids (y-axis)
      states     : dict[(cycle, tile_id)] -> (state, op, annotation)
    """
    tile_set = set(active_tiles)
    cycles = []
    states = {}
    for rec in records:
        c = rec['cycle']
        cycles.append(c)
        tile_map = {t['id']: t for t in rec['tiles']}
        for tid in active_tiles:
            if tid in tile_map:
                states[(c, tid)] = classify_tile(tile_map[tid], width, height)
            else:
                states[(c, tid)] = (S_IDLE, '', '')
    return cycles, active_tiles, states


# ── Color scheme ───────────────────────────────────────────────────────

STATE_COLORS = {
    S_IDLE:      '#E8E8E8',   # light gray
    S_EXEC:      '#4CAF50',   # green
    S_ROUTING:   '#2196F3',   # blue  – routing / data forwarding
    S_WAIT_UP:   '#FF9800',   # orange
    S_WAIT_DOWN: '#F44336',   # red
}


# ── Plot ────────────────────────────────────���──────────────────────────

def plot_timeline(cycles, tile_ids, states, width, height, out_path,
                  trace_name=''):
    n_cycles = len(cycles)
    n_tiles  = len(tile_ids)

    if n_cycles == 0 or n_tiles == 0:
        print("Nothing to plot.")
        return

    # Map tile_id → y index
    tid2y = {tid: i for i, tid in enumerate(tile_ids)}

    # Figure sizing: each cell ~ 0.35 wide, 0.5 tall
    cell_w = 0.35
    cell_h = 0.55
    fig_w = max(12, n_cycles * cell_w + 3)
    fig_h = max(4, n_tiles * cell_h + 2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))

    for ci, c in enumerate(cycles):
        for ti, tid in enumerate(tile_ids):
            state, op, ann = states.get((c, tid), (S_IDLE, '', ''))
            color = STATE_COLORS[state]
            rect = mpatches.FancyBboxPatch(
                (ci, ti - 0.4), 0.9, 0.8,
                boxstyle="round,pad=0.05",
                facecolor=color, edgecolor='white', linewidth=0.5)
            ax.add_patch(rect)

            # Operation label
            if state != S_IDLE:
                # Shorten op symbol: strip parens
                label = op.strip('()')
                fontsize = 6 if len(label) <= 6 else 5
                ax.text(ci + 0.45, ti + 0.05, label,
                        ha='center', va='center', fontsize=fontsize,
                        fontweight='bold',
                        color='white' if state != S_IDLE else '#888')

                # Annotation (who is being waited on)
                if ann:
                    ax.text(ci + 0.45, ti - 0.22, ann,
                            ha='center', va='center', fontsize=4,
                            color='white', style='italic')

    # Axes
    # X axis: cycle numbers
    tick_step = max(1, n_cycles // 40)
    xticks = list(range(0, n_cycles, tick_step))
    ax.set_xticks([x + 0.45 for x in xticks])
    ax.set_xticklabels([str(cycles[x]) for x in xticks], fontsize=6,
                       rotation=45)
    ax.set_xlabel('Cycle', fontsize=10)

    # Y axis: tile id with (col, row)
    ax.set_yticks(range(n_tiles))
    ylabels = []
    for tid in tile_ids:
        col = tid % width
        row = tid // width
        ylabels.append(f'Tile {tid}\n({col},{row})')
    ax.set_yticklabels(ylabels, fontsize=7)
    ax.set_ylabel('Tile', fontsize=10)

    ax.set_xlim(-0.2, n_cycles + 0.2)
    ax.set_ylim(-0.6, n_tiles - 0.4)
    ax.invert_yaxis()
    ax.set_aspect('auto')

    # Legend
    legend_patches = [
        mpatches.Patch(color=STATE_COLORS[S_EXEC],      label='Executing (FU)'),
        mpatches.Patch(color=STATE_COLORS[S_ROUTING],    label='Routing (DATA_MOV)'),
        mpatches.Patch(color=STATE_COLORS[S_WAIT_UP],    label='Wait upstream (input)'),
        mpatches.Patch(color=STATE_COLORS[S_WAIT_DOWN],  label='Wait downstream (output)'),
        mpatches.Patch(color=STATE_COLORS[S_IDLE],       label='Idle'),
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize=7,
              framealpha=0.9)

    title = 'CGRA Execution Timeline'
    if trace_name:
        title += f'  —  {trace_name}'
    ax.set_title(title, fontsize=12, fontweight='bold')

    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches='tight')
    print(f"Saved to {out_path}")
    plt.close()


# ── Main ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Plot CGRA execution timeline from JSONL trace')
    parser.add_argument('trace', help='Path to .jsonl trace file')
    parser.add_argument('--start', type=int, default=None,
                        help='First cycle to plot')
    parser.add_argument('--end', type=int, default=None,
                        help='Last cycle to plot')
    parser.add_argument('--out', type=str, default=None,
                        help='Output image path (default: <trace>_timeline.svg)')
    args = parser.parse_args()

    records = load_trace(args.trace, args.start, args.end)
    if not records:
        print("No records in the given cycle range.", file=sys.stderr)
        sys.exit(1)

    width  = records[0]['width']
    height = records[0]['height']

    active_tiles = find_active_tiles(records, width, height)
    cycles, tile_ids, states = build_timeline(records, active_tiles,
                                              width, height)

    out_path = args.out
    if out_path is None:
        base = os.path.splitext(args.trace)[0]
        out_path = f'{base}_timeline.svg'

    trace_name = os.path.basename(args.trace)
    plot_timeline(cycles, tile_ids, states, width, height, out_path,
                  trace_name)


if __name__ == '__main__':
    main()
