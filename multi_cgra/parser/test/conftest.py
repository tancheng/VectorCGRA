import os
"""
    Use `pytest Parser_test.py --arch_file /path/to/arch/file` to execute the test case of parser.
"""
def pytest_addoption(parser):
    parser.addoption(
        "--arch_file",
        action="store",
        default=os.path.join(os.path.dirname(__file__),"arch.yaml"),
        help="Path to the architecture YAML file. Relative paths are resolved from the current terminal directory."
    )