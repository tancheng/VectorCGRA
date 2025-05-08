#!/bin/bash

echo ${VERILATOR_ROOT}
echo ${PYMTL_VERILATOR_INCLUDE_DIR}
verilator --version

cd ${HOME}/cgra/VectorCGRA/build
source ${HOME}/venv/bin/activate
