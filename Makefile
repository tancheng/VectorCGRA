simple:
	cd cgra/test && \
	pytest STEP_CgraRTL_mapped.py::test_simple --tb=short -v --test-verilog --dump-vtb --dump-vcd --full-trace -s > out.log