__author__ = 'michal'

from ceilometer.openstack.common import log

LOG = log.getLogger(__name__)

W1, W2, W3 = 1, 1, 1

class Vm(object):

    def _get_last(self, list):

        return list[len(list) - 1]

    def __init__(self, rrdWrapper, name, hostName, cpu_speed, startDate, endDate):

        self.Hostname = hostName

#        cpu_util = rrdWrapper.query(startDate, endDate, "vcpu_util", name, hostName)[2][1][0]
#        cpu_num = rrdWrapper.query(startDate, endDate, "vcpu_num", name, hostName)[2][1][0]
#        pkts_in = rrdWrapper.query(startDate, endDate, "vpkts_in", name, hostName)[2][1][0]
#        pkts_out = rrdWrapper.query(startDate, endDate, "vpkts_out", name, hostName)[2][1][0]
#        mem_declared = rrdWrapper.query(startDate, endDate, "vmem_total", name, hostName)[2][1][0]

        cpu_util_series = rrdWrapper.query(startDate, endDate, "vcpu_util", name, hostName).Series
        cpu_num_series = rrdWrapper.query(startDate, endDate, "vcpu_num", name, hostName).Series
        pkts_in_series = rrdWrapper.query(startDate, endDate, "vpkts_in", name, hostName).Series
        pkts_out_series = rrdWrapper.query(startDate, endDate, "vpkts_out", name, hostName).Series
        mem_declared_series = rrdWrapper.query(startDate, endDate, "vmem_total", name, hostName).Series

        cpu_util = self._get_last(cpu_util_series)[0]
        cpu_num = self._get_last(cpu_num_series)[0]
        pkts_in = (pkts_in_series[0][0]. self._get_last(pkts_in_series)[0])
        pkts_out = (pkts_out_series[0][0]. self._get_last(pkts_out_series)[0])
        mem_declared = self._get_last(mem_declared_series)[0]

        LOG.info("cpu_util %s cpu_num %s pckts_in %s pckts_out %s mem_declared %s", cpu_util, cpu_num, pkts_in, pkts_out, mem_declared)

        self._cpu_util = cpu_util / 100
        self._cpu_num = cpu_num
        self._pkts_in = pkts_in
        self._pkts_out = pkts_out
        self._mem_declared = mem_declared
        self._cpu_speed = cpu_speed
        self._mem = 0
        self._bandwidth = ((pkts_in[1] - pkts_in[0]) + (pkts_out[1] - pkts_out[0])) / ((endDate - startDate).seconds)


    def getCValue(self):
        return self._cpu_num * self._cpu_speed * self._cpu_util

    def getNValue(self):
        return self._pkts_in + self._pkts_out #??

    def getMValue(self):
        return self._mem

    def getMWeight(self, host):
        return W1 * self.getC(host) + W2 * self._mem_declared + W3 * self.getN(host)

    def setMem(self, host, m_weight_sum):
        self._mem = host._mem * host._mem_util / m_weight_sum * self.getMWeight(host)


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
