The fixed-point functional unit's SystemVerilog RTL code is located in svsrc/. At the same level as this README file, there are two PyMTL wrappers. AluGenMacRTL.py encapsulates the SystemVerilog RTL code and makes it compatible with the PyMTL framework. AluGenMacWrapperRTL.py encapsulates the AluGenMacRTL.py SystemVerilog-to-PyMTL wrapper to make it compatible with the VectorCGRA framework. Both levels of abstraction can be verified using their respective tests in the test/ directory.

The SystemVerilog code instantiates a DesignWare module that is linked as an external dependency to this repo. The git submodule update --init command ensures that the submodule is exported correctly, as described in the repo's main README.

Publication
--------------------------------------------------------
```
@inproceedings{jokai2024fused,
  title={Fused Functional Units for Area-Efficient CGRAs},
  author={Jokai, Ron and Tan, Cheng and Zhang, Jeff Jun},
  booktitle={2024 25th International Symposium on Quality Electronic Design (ISQED)},
  pages={1--8},
  year={2024},
  organization={IEEE}
}
```
