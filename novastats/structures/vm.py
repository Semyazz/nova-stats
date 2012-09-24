__author__ = 'michal'

from ceilometer.openstack.common import log
from novastats.rrd import rrd
import math

LOG = log.getLogger(__name__)

class Vm(object):



    def __init__(self,
                 hostName,
                 instanceName,
                 cpu_util,
                 cpu_num,
                 pkts_in,
                 pkts_out,
                 mem_declared,
                 cpu_speed):

        self.Hostname = hostName
        self.InstanceName = instanceName



        LOG.error("vm: %s\t"
                  "cpu_util %s\t"
                  "cpu_num %s\t"
                  "pckts_in %s\t"
                  "pckts_out %s\t"
                  "mem_declared %s",
            instanceName,
            cpu_util,
            cpu_num,
            pkts_in,
            pkts_out,
            mem_declared)

        self._cpu_util = cpu_util / 100.0
        self._cpu_num = cpu_num
        self._pkts_in = pkts_in
        self._pkts_out = pkts_out
        self._mem_declared = mem_declared
        self._cpu_speed = cpu_speed
        self._mem = 0

    def getCValue(self):
        #LOG.error("cpu_value %s", self._cpu_num * self._cpu_speed * self._cpu_util)
        return self._cpu_num * self._cpu_speed * self._cpu_util

    def getNValue(self):
        return self._pkts_in + self._pkts_out #??

    def getMValue(self):
        return self._mem

    def getMWeight(self, host):
    #return self.wC * self.getC(host) + self.wM * self._mem_declared + self.wN * self.getN(host) #first (dump) version
    #return max( self.wM * (self.getC(host) + self.getN(host)) / 2.0 * self._mem_declared, self._mem_declared)

        first = max(256, (self.getC(host) + self.getN(host)) / 2.0 * self._mem_declared)
        weight = min(first  + self.wM * self._mem_declared, self._mem_declared)

        assert weight > 0, "Weight == 0"

        return weight


    def setMem(self, host, m_weight_sum):
        self._mem = host._mem * host._mem_util / m_weight_sum * self.getMWeight(host)

        #LOG.info("%s * %s / %s * %s = %s " %
        #         (host._mem, host._mem_util, m_weight_sum ,self.getMWeight(host), self._mem))
        #self._mem =  self._mem_declared #mem declared



    def getC (self, host):
        return self.getCValue() / float(host._cpu)

    def getN(self, host):
        return self.getNValue() / float(host._bandwidth)

    def getM(self, host):
        return self.getMValue() / float(host._mem)

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

    def getWeights(self):
        return self.wM

    def setWeights(self, weight):
        if weight is None:
            self.wM = 1
        else:
            self.wM = weight


    def modifyC(self, dif):
        self.wC += 0.01 * math.trunc(dif)

    def modifyN(self, dif):
        self.wN += 0.01 * math.trunc(dif)

    def modifyM(self, dif):

        old = self.wM

        self.wM += 0.01 * math.trunc(dif)

        if  self.wM < -1:
            self.wM = -1
        elif self.wM > 1:
            self.wM = 1

        LOG.error('Weight for instance %s changed to from %s to %s', self.InstanceName, old, self.wM)

