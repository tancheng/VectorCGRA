  Brief explanation about the control signal fields
  ----
  
  CtrlType(`optType`, `isCurOptPredicateBased`, `[registersUsedForComputation]`, `[portsWithDataToBeRouted]`, `[predicatesForFutureComputation]`)
  - `optType` can be found in lib/opt_type.py, there are currently more or less 40 operation/computation types supported, which represented in 6 bits.
  - `isCurOptPredicateBased` indicates whether this operation is predicate-based. Specifically, if set as `false`, this operation will be executed.
    If `true`, the execution of this operation depends on the predicate bit embedded in the data message. Normally, the predicate in the data message
     is calculated by the `phi` operation (to enable control-flow). Just set this field as `b1(0)` if no control-flow is involved.
  - `[registersUsedForComputation]` is a list contains `num_fu_in` (i.e., 4 in this case) items. It indicates the register ID that will be used
    for computation. There are 4 possible inputs in this tile configuration, so the length of the list is 4. Note that maybe less than 4 operations
    are used for computations. For example, `NOT` requires one, `Add` requires two, `MAC` requires three, and the complex FU that contains two
    parallel adders require four. In addition, the register ID starts from 1 as 0 is reserved to indicate invalid. For example, if data `a` is
    located in the second register while data `b` is located in the first register, to perform `a - b`, `[registersUsedForComputation]` should be
    set as `[2,1,0,0]`.
  - `[portsWithDataToBeRouted]` indicates how the data will be routed on the xbar. It contains `num_xbar_outports` items, which means each outport
    picks one inport for data delivery. In this case, we can see there are 8 items. The first 4 are the tile's outports (i.e., North, South, West,
    East). The second 4 are the 4 registers used for computation (i.e., `[registersUsedForComputation]`). Each item can choose the value ranging
    from 0 to 6. 0 is reserved indicating invalid, 1-4 indicate the inport N, S, W, and E. And 5-6 indicate the two outports of the functional unit.
  - `[predicatesForFutureComputation]` is used to indicate that the predicate bit in the result message will be calculated based on the data coming
    from this port. Ignore this field if no control-flow is involved.
