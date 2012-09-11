__author__ = 'michal'

from novastats.rrd import rrd

class Host(object):

    def _init(self, name, startDate, endDate):
        self._bandwidth = 10480
        self._cpu_util = 0
        self._cpu_num = 0
        self._cpu_speed = 0
        self._mem = 0
        self._mem_util = 0

        self._cpu = self._cpu_num * self._cpu_speed * self._cpu_util / 100

        self._vms = []

        mWeightSum = self.getMWeightSum()
        for vmi in self._vms:
            vmi.setMem(self, mWeightSum)



    def getMWeightSum(self):
        m_weight_sum = 0

        for vmi in self._vms:
            m_weight_sum += vmi.getMWeight(self)

        return m_weight_sum


    def getMetrics(self):

        vmValues = [vmi.getValues() for vmi in self._vms]

        cValue = 0
        nValue = 0
        mValue = 0

        for vmValue in vmValues:
            cValue += vmValue["C"]
            nValue += vmValue["N"]
            mValue += vmValue["M"]

        return {
            "C" : cValue / self._cpu * 100,
            "N" : nValue / self._bandwidth * 100,
            "M" : mValue / self._mem * 100,
        }
