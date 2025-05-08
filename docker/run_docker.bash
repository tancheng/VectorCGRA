#!/bin/bash

export PATH="${HOME}/verilator/bin:$PATH"
export VERILATOR_ROOT=${HOME}/verilator
export PYMTL_VERILATOR_INCLUDE_DIR=${HOME}/verilator/share/verilator/include
echo ${VERILATOR_ROOT}
echo ${PYMTL_VERILATOR_INCLUDE_DIR}
verilator --version

cd ${HOME}/cgra/VectorCGRA
mkdir -p build && cd build
source ${HOME}/venv/bin/activate

tail -f /dev/null
