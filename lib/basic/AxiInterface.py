from pymtl3 import *
from ...lib.util.common import *

class SendAxiReadLoadAddrIfcRTL( Interface ):
    def construct( s, DataType ):
        # Example uses 128 bit transfers
        # REQUIRED AXI Address Channel
        s.addr  = OutPort( AXI_ADDR_BITWIDTH )  # Load address
        s.addr_val = OutPort( 1 )   # Address valid
        s.addr_rdy = InPort( 1 )    # Address ready
        
        # OPTIONAL - can be tied to constants
        s.cache = OutPort( 4 )   # Cache type
        s.len   = OutPort( 8 )   # Burst length 
        s.size  = OutPort( 3 )   # Transfer size, because 2^4 can be 128
        s.burst = OutPort( 2 )   # Burst type
        s.id    = OutPort( clog2(MAX_THREAD_COUNT) )   # Transaction ID

        # REQUIRED AXI Data Channel  
        s.data   = InPort( DataType )  # Loaded data
        s.data_valid  = InPort( 1 )    # Data valid
        s.data_ready  = OutPort( 1 )   # Ready to receive data

        s.resp   = InPort( 2 )    # Response (can ignore)
        s.resp_last   = InPort( 1 )    # Last beat (can ignore for single)
        s.resp_id     = InPort( clog2(MAX_THREAD_COUNT) )    # Response ID (can ignore)

class SendAxiReadStoreAddrIfcRTL( Interface ):
    def construct( s, DataType ):
        # Example uses 128 bit transfers
        # REQUIRED AXI Address Channel
        s.addr  = OutPort( AXI_ADDR_BITWIDTH )  # Load address
        s.addr_val = OutPort( 1 )   # Address valid
        s.addr_rdy = InPort( 1 )    # Address ready
        
        # OPTIONAL - can be tied to constants
        s.cache = OutPort( 4 )   # Cache type
        s.len   = OutPort( 8 )   # Burst length 
        s.size  = OutPort( 3 )   # Transfer size, because 2^4 can be 128
        s.burst = OutPort( 2 )   # Burst type
        s.id    = OutPort( clog2(MAX_THREAD_COUNT) )   # Transaction ID

        # REQUIRED AXI Data Channel  
        s.data   = OutPort( DataType )  # Loaded data
        s.data_valid  = OutPort( 1 )    # Data valid
        s.data_ready  = OutPort( 1 )   # Ready to receive data

        s.str_bytes   = OutPort( 16 )  # Write strobes (byte enables) # ONLY STORE
        s.resp_valid  = InPort( 1 )    # Write response valid
        s.resp_ready  = OutPort( 1 )   # Write response ready

        s.resp   = InPort( 2 )    # Response (can ignore)
        s.resp_last   = InPort( 1 )    # Last beat (can ignore for single)
        s.resp_id     = InPort( clog2(MAX_THREAD_COUNT) )    # Response ID (can ignore)

class RecvAxiReadLoadAddrIfcRTL( Interface ):
    def construct( s, DataType, addr_nbits=AXI_ADDR_BITWIDTH ):
        # Example uses 128 bit transfers
        # REQUIRED AXI Address Channel
        s.addr     = InPort( addr_nbits )  # Load address
        s.addr_val = InPort( 1 )   # Address valid
        s.addr_rdy = OutPort( 1 )    # Address ready
        
        # OPTIONAL - can be tied to constants
        s.cache = InPort( 4 )   # Cache type
        s.len   = InPort( 8 )   # Burst length 
        s.size  = InPort( 3 )   # Transfer size, because 2^4 can be 128
        s.burst = InPort( 2 )   # Burst type
        s.id    = InPort( clog2(MAX_THREAD_COUNT) )   # Transaction ID

        # REQUIRED AXI Data Channel  
        s.data        = OutPort( DataType )  # Loaded data
        s.data_valid  = OutPort( 1 )    # Data valid
        s.data_ready  = InPort( 1 )   # Ready to receive data

        s.resp_valid  = OutPort( 1 )    # Write response valid
        s.resp_ready  = InPort( 1 )   # Write response ready
        s.resp        = OutPort( 2 )    # Response (can ignore)
        s.resp_last   = OutPort( 1 )    # Last beat (can ignore for single)
        s.resp_id     = OutPort( clog2(MAX_THREAD_COUNT) )    # Response ID (can ignore)

class RecvAxiReadStoreAddrIfcRTL( Interface ):
    def construct( s, DataType, addr_nbits=AXI_ADDR_BITWIDTH ):
        # Example uses 128 bit transfers
        # REQUIRED AXI Address Channel
        s.addr     = InPort( addr_nbits )  # Load address
        s.addr_val = InPort( 1 )   # Address valid
        s.addr_rdy = OutPort( 1 )    # Address ready
        
        # OPTIONAL - can be tied to constants
        s.cache = InPort( 4 )   # Cache type
        s.len   = InPort( 8 )   # Burst length 
        s.size  = InPort( 3 )   # Transfer size, because 2^4 can be 128
        s.burst = InPort( 2 )   # Burst type
        s.id    = InPort( clog2(MAX_THREAD_COUNT) )   # Transaction ID

        # REQUIRED AXI Data Channel  
        s.data        = InPort( DataType )  # Loaded data
        s.data_valid  = InPort( 1 )    # Data valid
        s.data_ready  = InPort( 1 )   # Ready to receive data

        s.str_bytes   = InPort( 16 )  # Write strobes (byte enables) # ONLY STORE
        s.resp_valid  = OutPort( 1 )    # Write response valid ONLY STORE
        s.resp_ready  = InPort( 1 )   # Write response ready ONLY STORE

        s.resp        = OutPort( 2 )    # Response (can ignore)
        s.resp_last   = OutPort( 1 )    # Last beat (can ignore for single)
        s.resp_id     = OutPort( clog2(MAX_THREAD_COUNT) )    # Response ID (can ignore)


class RecvAxiStoreIfcRTL( Interface ):
    def construct( s, DataType, addr_nbits=AXI_ADDR_BITWIDTH ):
        # Load unit interface
        s.i_addr = InPort( addr_nbits )                 # Store Address
        s.i_data = InPort( DataType )     # Store Data
        s.i_req = InPort( 1 )                   # Request Store
        s.o_rdy = OutPort( 1 )                   # Ready to receive store request
        s.o_done = OutPort( 1 )                 # Complete

class RecvAxiLoadIfcRTL( Interface ):
    def construct( s, DataType, addr_nbits=AXI_ADDR_BITWIDTH ):
        # Load unit interface
        s.i_addr = InPort( addr_nbits )                 # Load Address
        s.i_req = InPort( 1 )                   # Request Load
        s.o_rdy = OutPort( 1 )                   # Ready to receive load request
        s.o_data = OutPort( DataType )    # Loaded Data
        s.o_done = OutPort( 1 )                 # Complete
        s.o_data_id = OutPort( clog2(MAX_THREAD_COUNT) ) # Thread Id associated w/ Data
