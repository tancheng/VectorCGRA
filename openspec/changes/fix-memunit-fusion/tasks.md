## 1. Implementation

### Combo FU Memory Port Propagation
- [x] 1.1 Modify `fu/basic/TwoSeqCombo.py` to propagate memory interfaces from internal FUs using OR logic
- [x] 1.2 Modify `fu/basic/TwoPrlCombo.py` to propagate memory interfaces from internal FUs using OR logic
- [x] 1.3 Modify `fu/basic/ThreeCombo.py` to propagate memory interfaces from internal FUs using OR logic
- [x] 1.4 Modify `fu/basic/FourCombo.py` to propagate memory interfaces from internal FUs using OR logic

### TileRTL Memory Connection Logic
- [x] 1.5 Update `tile/TileRTL.py` to detect combo FUs containing `MemUnitRTL` and connect their memory ports

## 2. Testing
- [x] 2.1 Add unit test for combo FU with `MemUnitRTL` - created `fu/double/SeqAdderMemRTL.py` and `fu/double/test/SeqAdderMemRTL_test.py`
- [x] 2.2 Add tile-level test verifying memory-compute fusion works - added `test_tile_combo_fu_with_memunit` in `tile/test/TileRTL_test.py`
- [ ] 2.3 Run existing tests to ensure no regression

## 3. Validation
- [ ] 3.1 Verify Verilog translation works with `--test-verilog`
- [ ] 3.2 Run full test suite to ensure backward compatibility
