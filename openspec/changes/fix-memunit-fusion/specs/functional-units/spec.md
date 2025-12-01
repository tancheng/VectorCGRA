## ADDED Requirements

### Requirement: Combo FU Memory Interface Propagation
Combo FUs (TwoSeqCombo, TwoPrlCombo, ThreeCombo, FourCombo) SHALL propagate memory interface signals from their internal FUs to their external memory ports when any internal FU is a memory-capable unit.

The memory signals to propagate are:
- `to_mem_raddr` (read address output)
- `from_mem_rdata` (read data input)
- `to_mem_waddr` (write address output)
- `to_mem_wdata` (write data output)

The propagation SHALL use OR logic to combine signals from all internal FUs, since non-memory FUs tie their memory ports to 0.

#### Scenario: TwoSeqCombo with MemUnitRTL as second FU
- **WHEN** a TwoSeqCombo is constructed with MemUnitRTL as Fu1
- **AND** the combo FU receives a load operation
- **THEN** the memory read address from the internal MemUnitRTL SHALL be propagated to the combo's `to_mem_raddr` port
- **AND** the memory read data received on `from_mem_rdata` SHALL be propagated to the internal MemUnitRTL

#### Scenario: Combo FU without MemUnitRTL
- **WHEN** a combo FU is constructed with no internal MemUnitRTL
- **THEN** all memory ports SHALL remain at their default values (0)
- **AND** backward compatibility SHALL be maintained

### Requirement: TileRTL Combo FU Memory Detection
TileRTL SHALL detect when a functional unit in its FuList is a combo FU containing MemUnitRTL and connect the tile's memory ports to that combo FU's memory interfaces.

#### Scenario: Tile with combo FU containing MemUnitRTL
- **WHEN** TileRTL is constructed with a FuList containing a combo FU that includes MemUnitRTL
- **THEN** the tile's memory interfaces SHALL be connected to that combo FU's memory ports
- **AND** memory operations within the combo FU SHALL function correctly

#### Scenario: Tile with standalone MemUnitRTL (backward compatibility)
- **WHEN** TileRTL is constructed with a FuList containing a standalone MemUnitRTL
- **THEN** the existing behavior SHALL be preserved
- **AND** the tile's memory interfaces SHALL be connected to MemUnitRTL's memory ports
