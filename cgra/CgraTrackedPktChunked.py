class CgraTrackedPktChunked:
    """
    Wrapper that automatically chunks packets into 32-bit pieces
    while maintaining the same interface as the original packet memory
    """

    @staticmethod
    def chunk_packet_to_32bits(packet):
        """Convert a single IntraCGRA packet to list of 32-bit chunks"""
        packet_bits = int(packet)
        packet_width = packet.nbits
        chunk_size = 32
        
        chunks = []
        for i in range((packet_width + chunk_size - 1) // chunk_size):  # Ceiling division
            bit_start = i * chunk_size
            bit_end = min(bit_start + chunk_size, packet_width)
            
            # Extract the chunk
            mask = (1 << (bit_end - bit_start)) - 1
            chunk = (packet_bits >> bit_start) & mask
            chunks.append(chunk)
        
        return chunks
    
    def __init__(self, IntraCgraPktType, chunk_size = 32):
        self.IntraCgraPktType = IntraCgraPktType
        self.packet_width = IntraCgraPktType.nbits
        self.chunks_per_packet = (self.packet_width + chunk_size - 1) // chunk_size  # Ceiling division
        self.chunked_memory = []
        self.packet_count = 0
        
    def add_packet(self, packet):
        """Add a single packet (gets automatically chunked)"""
        chunks = CgraTrackedPktChunked.chunk_packet_to_32bits(packet)
        self.chunked_memory.extend(chunks)
        self.packet_count += 1
        
    def add_packets(self, packet_list):
        """Add a list of packets (gets automatically chunked)"""
        for packet in packet_list:
            self.add_packet(packet)
            
    def extend(self, packet_list):
        """Mimic list.extend() behavior"""
        self.add_packets(packet_list)
        
    def get_32bit_chunks(self):
        """Get the flat list of chunk_size chunks"""
        return self.chunked_memory
        
    def get_chunk_count(self):
        """Get total number of 32-bit chunks"""
        return len(self.chunked_memory)
        
    def get_packet_count(self):
        """Get number of original packets"""
        return self.packet_count
        
    def clear(self):
        """Clear all stored data"""
        self.chunked_memory = []
        self.packet_count = 0
        
    def __len__(self):
        """Return number of 32-bit chunks"""
        return len(self.chunked_memory)
        
    def __getitem__(self, index):
        """Get chunk by index"""
        return self.chunked_memory[index]