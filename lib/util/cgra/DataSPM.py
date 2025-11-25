class DataSPM:
    def __init__(s, numOfReadPorts, numOfWritePorts):
        s.numOfReadPorts = numOfReadPorts
        s.numOfWritePorts = numOfWritePorts

    def getNumOfValidReadPorts(s):
        return s.numOfReadPorts

    def getNumOfValidWritePorts(s):
        return s.numOfWritePorts
