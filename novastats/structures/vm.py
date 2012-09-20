__author__ = 'michal'

from ceilometer.openstack.common import log
from novastats.rrd import rrd
import math

LOG = log.getLogger(__name__)

class Vm(object):



    def __init__(self, rrdWrapper, instanceName, hostName, cpu_speed, endTime, weights=None):

        self.Hostname = hostName
        self.InstanceName = instanceName

        self.setWeights(weights)

        cpu_util = rrd.getWeightedAverageData(rrdWrapper, endTime, "vcpu_util", hostName, instanceName)
        cpu_num = rrd.getSingleValue(rrdWrapper, endTime, "vcpu_num", hostName, instanceName)
        pkts_in = rrd.getWeightedAverageData(rrdWrapper, endTime, "vpkts_in", hostName, instanceName)
        pkts_out = rrd.getWeightedAverageData(rrdWrapper, endTime, "vpkts_out", hostName, instanceName)
        mem_declared = rrd.getSingleValue(rrdWrapper, endTime, "vmem_total", hostName, instanceName)

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

        self._cpu_util = cpu_util / 100
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
        return self.wC * self.getC(host) + self.wM * self._mem_declared + self.wN * self.getN(host)

    def setMem(self, host, m_weight_sum):
        self._mem = host._mem * host._mem_util / m_weight_sum * self.getMWeight(host)
        #self._mem =  self._mem_declared


    def getC (self, host):
         return self.getCValue() / host._cpu

    def getN(self, host):
        return self.getNValue() / host._bandwidth

    def getM(self, host):
        return self.getMValue() / host._mem

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
        return {
            "C" : self.wC,
            "N" : self.wN,
            "M" : self.wM,
        }

    def setWeights(self, weights):
        if weights is None:
            self.wC = 1
            self.wN = 1
            self.wM = 1
        else:
            self.wC = weights["C"]
            self.wN = weights["N"]
            self.wM = weights["M"]


    def modifyC(self, dif):
        self.wC += 0.01 * math.trunc(dif)

    def modifyN(self, dif):
        self.wN += 0.01 * math.trunc(dif)

    def modifyM(self, dif):
        self.wM += 0.01 * math.trunc(dif)