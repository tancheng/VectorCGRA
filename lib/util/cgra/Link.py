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

    """
    Validates the ports of the link.
    If the link is not disabled, the ports are removed from the invalidOutPorts and invalidInPorts of the srcTile and dstTile.
      - If the link is to memory, the toMem flag of the srcTile is set to True.
      - If the link is from memory, the fromMem flag of the dstTile is set to True.
    If the link is disabled, the ports are added to the invalidOutPorts and invalidInPorts of the srcTile and dstTile.
      - If the link is to memory, the toMem flag of the srcTile is set to False.
      - If the link is from memory, the fromMem flag of the dstTile is set to False.
    """
    if not s.disabled:
      if not s.toMem and not s.fromMem:
        # the link is between two tiles.
        s.srcTile.invalidOutPorts.remove(s.srcPort)
        s.dstTile.invalidInPorts.remove(s.dstPort)
      elif s.toMem:
        s.srcTile.invalidOutPorts.remove(s.srcPort)
        s.srcTile.toMem = True
      elif s.fromMem:
        s.dstTile.invalidInPorts.remove(s.dstPort)
        s.dstTile.fromMem = True
    else:# the link is disabled.
      if not s.toMem and not s.fromMem:
        # the link is between two tiles.
        s.srcTile.invalidOutPorts.add(s.srcPort)
        s.dstTile.invalidInPorts.add(s.dstPort)
      elif s.toMem:
        # the link is to memory.
        s.srcTile.invalidOutPorts.add(s.srcPort)
        s.srcTile.toMem = False
      elif s.fromMem:
        # the link is from memory.
        s.dstTile.invalidInPorts.add(s.dstPort)
        s.dstTile.fromMem = False
