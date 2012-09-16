__author__ = 'michal'

from ceilometer.openstack.common import log

LOG = log.getLogger(__name__)

W1, W2, W3 = 1, 1, 1

class Vm(object):



    def __init__(self, rrdWrapper, name, hostName, cpu_speed, startDate, endDate):

        self.Hostname = hostName
        self.InstanceName = name
#        cpu_util = rrdWrapper.query(startDate, endDate, "vcpu_util", name, hostName)[2][1][0]
#        cpu_num = rrdWrapper.query(startDate, endDate, "vcpu_num", name, hostName)[2][1][0]
#        pkts_in = rrdWrapper.query(startDate, endDate, "vpkts_in", name, hostName)[2][1][0]
#        pkts_out = rrdWrapper.query(startDate, endDate, "vpkts_out", name, hostName)[2][1][0]
#        mem_declared = rrdWrapper.query(startDate, endDate, "vmem_total", name, hostName)[2][1][0]

        cpu_util = rrdWrapper.query(startDate, endDate, "vcpu_util", name, hostName).Average
        cpu_num = rrdWrapper.query(startDate, endDate, "vcpu_num", name, hostName).getLastSingleValue()
        pkts_in = rrdWrapper.query(startDate, endDate, "vpkts_in", name, hostName).Average
        pkts_out = rrdWrapper.query(startDate, endDate, "vpkts_out", name, hostName).Average
        mem_declared = rrdWrapper.query(startDate, endDate, "vmem_total", name, hostName).getLastSingleValue()

        LOG.error("vm: %s\t"
                  "cpu_util %s\t"
                  "cpu_num %s\t"
                  "pckts_in %s\t"
                  "pckts_out %s\t"
                  "mem_declared %s",
            name,
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
        return W1 * self.getC(host) + W2 * self._mem_declared + W3 * self.getN(host)

    def setMem(self, host, m_weight_sum):
        #self._mem = host._mem * host._mem_util / m_weight_sum * self.getMWeight(host)
        self._mem =  self._mem_declared


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
