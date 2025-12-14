from ..common import PORT_DIRECTION_COUNTS
class Tile:
  def __init__(s, dimX, dimY, num_registers, operations):
    s.disabled = False
    s.dimX = dimX
    s.dimY = dimY
    s.num_registers = num_registers
    s.operations = operations
    s.isDefaultFus_ = True
    s.toMem = False
    s.fromMem = False
    s.invalidOutPorts = set()
    s.invalidInPorts = set()
    for i in range(PORT_DIRECTION_COUNTS):
      s.invalidOutPorts.add(i)
      s.invalidInPorts.add(i)

  def getInvalidInPorts(s):
    return s.invalidInPorts

  def getInvalidOutPorts(s):
    return s.invalidOutPorts

  def hasToMem(s):
    return s.toMem

  def hasFromMem(s):
    return s.fromMem

  def getIndex(s, TileList):
    if s.disabled:
      return -1
    index = 0
    for tile in TileList:
      if tile.dimY < s.dimY and not tile.disabled:
        index += 1
      elif tile.dimY == s.dimY and tile.dimX < s.dimX and not tile.disabled:
        index += 1
    return index

  def isDefaultFus(s):
    return s.isDefaultFus_

  def getAllValidFuTypes(s):
    return s.operations
  
  def override(s):
    # TODO @benkangpeng
    raise NotImplementedError
