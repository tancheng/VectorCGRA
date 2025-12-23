This pure SystemVerilog testbench mimics the scalar FIR test of MeshMultiCgraRTL_test.py

It has two roles;

  1) Ensure that the generated SV code matches the functionality of the PyMTL code. (Highlighting issues such as missing DFF resets that can be overlooked by PyMTL.)
  2) Generate hex code that can serve as the contents of a RISC-V CPU's Imem, which, in turn, can program the co-located CGRA to execute operations dictated by this SV tb's generated hex code.

1) is accomplished by header.sv's three functions (make_intra_cgra_pkt, make_intra_cgra_config_pkt, make_intra_cgra_config_pkt_w_data) that create the same packets as implemented by the by the IntraCgraPktType data types in preload_data and src_opt_pkt in MeshMultiCgraRTL_test.py. 2) is also accomplished by the same three functions; in their second part, they print the necessary RISC-V hex code into a file for the CPU to load the shared Dmem with the appropriate config packets.

The SV tb implements the test_fir_scalar test of MeshMultiCgraRTL_test.py (12/20/2025 version). The PyMTL test has the following hardware parameters:

  o num_cgra_rows = 2,
  o num_cgra_columns = 2,
  o num_x_tiles_per_cgra = 4,
  o num_y_tiles_per_cgra = 4,
  o num_banks_per_cgra = 2,
  o data_mem_size_per_bank = 16,
  o mem_access_is_combinational = True.

