class Link:
  def __init__(s, srcTile, dstTile, srcPort, dstPort):
    s.srcTile = srcTile
    s.dstTile = dstTile
    s.srcPort = srcPort
    s.dstPort = dstPort
    s.disabled = False
    s.toMem = False
    s.fromMem = False
    s.memPort = -1

  def getMemReadPort(s):
      return s.memPort

  def getMemWritePort(s):
      return s.memPort

  def isToMem(s):
    return s.toMem

  def isFromMem(s):
    return s.fromMem

  def validatePorts(s):
    if not s.toMem and not s.fromMem:
      s.srcTile.invalidOutPorts.remove(s.srcPort)
      s.dstTile.invalidInPorts.remove(s.dstPort)
    if s.toMem:
      s.srcTile.toMem = True
    if s.fromMem:
      s.dstTile.fromMem = True
