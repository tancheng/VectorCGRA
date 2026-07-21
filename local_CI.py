"""
local_CI.py is a script that runs the CI tests locally.
Usage:
```shell
cd /path/to/VectorCGRA/
mkdir -p build && cd build
python3 local_CI.py
```
The log will be saved to the `local_CI.log` file.
"""
import subprocess
import os
import sys

def run_tests():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(current_dir, "local_CI.log")
    
    commands = [
        ["pytest", "..", "-v", "--tb=short"],
        ["pytest", "../mem/ctrl/test/CtrlMemDynamicRTL_test.py", "-xvs"],
        ["pytest", "../tile/test/TileRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../controller/test/ControllerRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../cgra/test/CgraTemplateRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../cgra/test/CgraRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../noc/PyOCN/pymtl3_net/ringnet/test/RingNetworkRTL_test.py"],
        ["pytest", "../multi_cgra/test/RingMultiCgraRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../multi_cgra/test/MeshMultiCgraRTL_test.py::test_verilog_homo_2x2_4x4", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../mem/const/test/ConstQueueDynamicRTL_test.py", "-xvs"],
        ["pytest", "../mem/data/test/DataMemControllerRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../multi_cgra/test/MeshMultiCgraTemplateRTL_test.py", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../multi_cgra/test/MeshMultiCgraRTL_test.py::test_multi_CGRA_fir_scalar_translation", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../multi_cgra/test/MeshMultiCgraRTL_test.py::test_multi_CGRA_fir_vector_global_reduce_translation", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"],
        ["pytest", "../multi_cgra/test/MeshMultiCgraRTL_test.py::test_multi_CGRA_systolic_2x2_2x2_translation", "-xvs", "--test-verilog", "--dump-vtb", "--dump-vcd"]
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        for cmd in commands:
            cmd_str = " ".join(cmd)
            header = f"\n{'='*80}\nExecuting: {cmd_str}\n{'='*80}\n"
            
            print(header)
            f.write(header)
            f.flush()

            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in process.stdout:
                    print(line, end="")
                    f.write(line)
                
                process.wait()
                
                if process.returncode == 0:
                    status = f"\nSUCCESS: {cmd_str}\n"
                else:
                    status = f"\nFAILED (Exit Code {process.returncode}): {cmd_str}\n"
                
                print(status)
                f.write(status)

            except Exception as e:
                error_msg = f"\nERROR executing {cmd_str}: {str(e)}\n"
                print(error_msg)
                f.write(error_msg)

    print(f"\n\nAll tests completed. Log saved to: {os.path.abspath(log_file)}")

if __name__ == "__main__":
    run_tests()