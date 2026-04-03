import json
found = False
with open('trace_output/trace_fir4x4_4x4_Mesh.jsonl', 'r') as f:
    for line in f:
        data = json.loads(line)
        cycle = data['cycle']
        for tile in data['tiles']:
            fu = tile['fu']
            if fu['operation_symbol'] == '(grant_once)':
                print(f"Cycle {cycle}: Tile ({tile['col']}, {tile['row']}) val={fu['recv_opt_val']} rdy={fu['recv_opt_rdy']} in0={fu['inputs'][0]} in1={fu['inputs'][1]} out={fu['outputs'][0]}")
                found = True
        if found and cycle > 40: # exit early after we start seeing it
             break
