#!/usr/bin/env python3

import re
import sys

def parse_verilog_cases(input_file, output_file):
    """
    Parse a .v cases file and extract 3rd and 6th index values.
    Creates C arrays based on the last index value.
    """
    input_pkt_index = 1
    input_pkt_v_index = 3
    output_pkt_index = 4
    output_pkt_v_index = 6
    # input_pkt_index = 3
    # input_pkt_v_index = 5
    # output_pkt_index = 6
    # output_pkt_v_index = -1
    
    tx_arrays = []
    rx_arrays = []
    
    # Pattern to match `T(...) lines
    pattern = r"`T\(([^)]+)\);"
    
    try:
        with open(input_file, 'r') as f:
            content = f.read()
            
        # Find all matches
        matches = re.findall(pattern, content)
        
        for match in matches:
            # Split by comma and clean up
            values = [val.strip().strip("'") for val in match.split(',')]
            
            if len(values) < 4:  # Need at least 9 values (0-8 indices)
                print(f"Warning: Skipping line with insufficient values: {values}")
                continue
                
            # Get 3rd index (index 3) and 6th index (index 6) 
            third_val = values[input_pkt_index]  # 4th value - the long hex config string
            sixth_val = values[output_pkt_index]  # 7th value - the long hex config string
            last_val = values[output_pkt_v_index]  # Last index
            
            # Convert hex values to integers, then to 32-bit chunks
            def hex_to_32bit_chunks(hex_str):
                # Remove 'h' prefix if present
                hex_str = hex_str.lstrip('h')
                
                # Pad to ensure we have multiples of 8 hex digits (32 bits)
                while len(hex_str) % 8 != 0:
                    hex_str = '0' + hex_str
                    
                # Split into 32-bit chunks (8 hex digits each) - REVERSE ORDER for little endian
                chunks = []
                for i in range(len(hex_str) - 8, -1, -8):
                    chunk = hex_str[i:i+8]
                    chunks.append(f"0x{chunk.upper()}")
                
                # Ensure we have exactly 6 elements (pad with zeros if needed)
                while len(chunks) < 6:
                    chunks.append("0x00000000")
                    
                return chunks[:6]  # Take only first 6
            
            # Only process if index 5 (6th value) is '1'
            fifth_val = values[input_pkt_v_index]  # Index 5 is values[4] in 0-based indexing
            
            if fifth_val == 'h1' or fifth_val == '1':
                # Convert third value (index 3) to tx_config entry
                tx_entry = hex_to_32bit_chunks(third_val)
                tx_arrays.append(tx_entry)
            
            # Only add to rx_config if last value is '1' (regardless of index 5)
            if last_val == 'h1' or last_val == '1':
                rx_entry = hex_to_32bit_chunks(sixth_val)
                rx_arrays.append(rx_entry)
                
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Write output
    try:
        with open(output_file, 'w') as f:
            # Write tx_config array
            f.write("u32 tx_config[][6] = {\n")
            for i, entry in enumerate(tx_arrays):
                f.write("    {" + ", ".join(entry) + "}")
                if i < len(tx_arrays) - 1:
                    f.write(",")
                f.write("\n")
            f.write("};\n\n")
            
            # Write rx_config array
            f.write("u32 rx_config[][6] = {\n")
            for i, entry in enumerate(rx_arrays):
                f.write("    {" + ", ".join(entry) + "}")
                if i < len(rx_arrays) - 1:
                    f.write(",")
                f.write("\n")
            f.write("};\n")
            
        print(f"Successfully wrote {len(tx_arrays)} tx_config entries and {len(rx_arrays)} rx_config entries to '{output_file}'")
        
    except Exception as e:
        print(f"Error writing output file: {e}")

def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_file.v> <output_file.c>")
        print("Example: python script.py test_cases.v config_arrays.c")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    parse_verilog_cases(input_file, output_file)

if __name__ == "__main__":
    main()