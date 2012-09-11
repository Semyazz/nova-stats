__author__ = 'michal'

from ceilometer.openstack.common import log
from novastats.structures.host import Host


LOG = log.getLogger(__name__)

W1, W2, W3 = 1, 1, 1

class Vm(object):

    def __init__(self, rrdWrapper, name, hostName, startDate, endDate):

        cpu_util = rrdWrapper(startDate, endDate, "cpu_util", name, hostName)
        cpu_num = rrdWrapper(startDate, endDate, "cpu_num", name, hostName)
        cpu_speed = rrdWrapper(startDate, endDate, "cpu_speed", name, hostName)
        pckts_in = rrdWrapper(startDate, endDate, "pckts_in", name, hostName)
        pckts_out = rrdWrapper(startDate, endDate, "pckts_out", name, hostName)
        mem_declared = rrdWrapper(startDate, endDate, "mem_declared", name, hostName)

        LOG.info("cpu_util %s cpu_num %s cpu_speed %s pckts_in %s pckts_out %s mem_declared %", cpu_util, cpu_num, cpu_speed, pckts_in, pckts_out, mem_declared)

        self._cpu_util = 0
        self._cpu_num = 0
        self._cpu_speed = 0
        self._pckts_in = 0
        self._pckts_out = 0
        self._mem_declared = 0
        self._mem = 0


    def getCValue(self):
        return self._cpu_num * self._cpu_speed * self._cpu_util / 100

    def getNValue(self):
        return self._pckts_in + self._pckts_out

    def getMValue(self):
        return self._mem

    def getMWeight(self, host):
        return W1 * self.getC(host) + W2 * self._mem_declared + W3 * self.getN(host)

    def setMem(self, host, m_weight_sum):
        self._mem = host._mem * host._mem_util / m_weight_sum * self.getMWeight(host)


    def getC (self, host):
         return self.getCValue() / host._cpu * 100

    def getN(self, host):
        return self.getNValue() / host._bandwidth * 100

    def getM(self, host):
        return self.getMValue() / host._mem * 100

    def getValues(self):

        return {
            "C" : self.getCValue(),
            "N" : self.getNValue(),
            "M" : self.getMValue(),
        }

    def getMetrics(self, host):

        return {
                "C" : self.getC(host),
                "N" : self.getN(host),
                "M" : self.getM(host),
               }
