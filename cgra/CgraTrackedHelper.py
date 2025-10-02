from pymtl3 import *

def convertPktToCPUWidth(pkt, cpu_width=32):
    """
    Convert a packet structure into chunks of specified CPU width (default 32 bits).
    Returns a list of chunks, each exactly cpu_width bits.
    """
    total_pkts = []
    all_data = []
    
    def process_packet_recursive(pkt_item):
        """Recursively collect all leaf data items from the packet structure"""
        nonlocal all_data
        
        # Base case: if it's a simple value without nested structure
        if not hasattr(pkt_item, '__dict__'):
            if hasattr(pkt_item, 'nbits'):
                all_data.append(pkt_item)
            return
        
        # Process each attribute in the packet
        for attr_name in vars(pkt_item):
            attr_value = getattr(pkt_item, attr_name)
            
            # Recursively process nested packet structures
            if hasattr(attr_value, '__dict__'):
                process_packet_recursive(attr_value)
            
            # Handle lists of packet items
            elif isinstance(attr_value, list):
                for item in attr_value:
                    process_packet_recursive(item)
            
            # Handle actual data fields
            else:
                if hasattr(attr_value, 'nbits'):
                    all_data.append(attr_value)
    
    # First pass: collect all data
    process_packet_recursive(pkt)
    
    if not all_data:
        return total_pkts
    
    # Simple approach: build one big bit string, then chunk it
    # This avoids complex bit slicing operations
    total_bits_needed = sum(item.nbits for item in all_data)
    
    # Create the target bit width type
    CpuWidthType = mk_bits(cpu_width)
    
    # Process data sequentially and build chunks
    current_chunk_value = 0
    current_chunk_bits = 0
    
    for data_item in all_data:
        # Convert data item to integer
        item_value = int(data_item)
        item_bits = data_item.nbits
        
        # Add this item's bits to our current chunk
        while item_bits > 0:
            # How much space left in current chunk?
            space_left = cpu_width - current_chunk_bits
            
            if space_left == 0:
                # Current chunk is full, emit it
                chunk = CpuWidthType(current_chunk_value)
                total_pkts.append(chunk)
                current_chunk_value = 0
                current_chunk_bits = 0
                space_left = cpu_width
            
            # How many bits can we take from current item?
            bits_to_take = min(space_left, item_bits)
            
            # Extract the bits we need
            mask = (1 << bits_to_take) - 1
            bits_value = item_value & mask
            
            # Add to current chunk
            current_chunk_value |= (bits_value << current_chunk_bits)
            current_chunk_bits += bits_to_take
            
            # Remove the bits we used from the item
            item_value >>= bits_to_take
            item_bits -= bits_to_take
    
    # Handle any remaining partial chunk
    if current_chunk_bits > 0:
        # Pad remaining bits are already 0, so just emit the chunk
        chunk = CpuWidthType(current_chunk_value)
        total_pkts.append(chunk)
    
    return total_pkts