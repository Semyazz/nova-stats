__author__ = 'michal'

from ceilometer.openstack.common import log
from structures.vm import Vm


LOG = log.getLogger(__name__)

class Host(object):

    def __init__(self, rrdWrapper, instances, name, startDate, endDate):

        cpu_system = rrdWrapper(startDate, endDate, "cpu_system", name, hostName)
        cpu_user = rrdWrapper(startDate, endDate, "cpu_user", name, hostName)
        cpu_num = rrdWrapper(startDate, endDate, "cpu_num", name, hostName)
        cpu_speed = rrdWrapper(startDate, endDate, "cpu_speed", name, hostName)
        mem = rrdWrapper(startDate, endDate, "mem", name, hostName)
        mem_util = rrdWrapper(startDate, endDate, "mem_util", name, hostName)

        LOG.info("cpu_system %s cpu_user %s cpu_num %s cpu_speed %s mem %s mem_util %s", cpu_system, cpu_user, cpu_num, cpu_speed, mem, mem_util)

        self._bandwidth = 10480
        self._cpu_util = 0
        self._cpu_num = 0
        self._cpu_speed = 0
        self._mem = 0
        self._mem_util = 0

        self._cpu = self._cpu_num * self._cpu_speed * self._cpu_util / 100

        instanceNames = instances[name]

        self._vms = []

        for instance in instanceNames:
            LOG.info("collecting data from instance %s", instance)
            self._vms.append(Vm(rrdWrapper,instance,name,startDate, endDate))

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
