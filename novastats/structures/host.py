__author__ = 'michal'

from ceilometer.openstack.common import log
from vm import Vm


LOG = log.getLogger(__name__)

class Host(object):

    def _get_last(self, list):

        return list[len(list) - 1]

    def __init__(self, rrdWrapper, instances, name, startDate, endDate):

#        cpu_system = rrdWrapper.query(startDate, endDate, "cpu_system", hostname = name)[2][1][0]
#        cpu_user = rrdWrapper.query(startDate, endDate, "cpu_user", hostname = name)[2][1][0]
#        cpu_num = rrdWrapper.query(startDate, endDate, "cpu_num", hostname = name)[2][1][0]
#        cpu_speed = rrdWrapper.query(startDate, endDate, "cpu_speed", hostname = name)[2][1][0]
#        mem = rrdWrapper.query(startDate, endDate, "mem_total", hostname = name)[2][1][0]
#        mem_free = rrdWrapper.query(startDate, endDate, "mem_free", hostname = name)[2][1][0]

        cpu_system_series = rrdWrapper.query(startDate, endDate, "cpu_system", hostname = name).Series
        cpu_user_series = rrdWrapper.query(startDate, endDate, "cpu_user", hostname = name).Series
        cpu_num_series = rrdWrapper.query(startDate, endDate, "cpu_num", hostname = name).Series
        cpu_speed_series = rrdWrapper.query(startDate, endDate, "cpu_speed", hostname = name).Series
        mem_series = rrdWrapper.query(startDate, endDate, "mem_total", hostname = name).Series
        mem_free_series = rrdWrapper.query(startDate, endDate, "mem_free", hostname = name).Series

        cpu_system = self._get_last(cpu_system_series)[0]
        cpu_user = self._get_last(cpu_user_series)[0]
        cpu_num = self._get_last(cpu_num_series)[0]
        cpu_speed = self._get_last(cpu_speed_series)[0]
        mem = self._get_last(mem_series)[0]
        mem_free = self._get_last(mem_free_series)[0]

        LOG.info("cpu_system %s cpu_user %s cpu_num %s cpu_speed %s mem %s mem_free %s", cpu_system, cpu_user, cpu_num, cpu_speed, mem, mem_free)

        self._bandwidth = 10480
        self._cpu_util = cpu_user + cpu_system
        self._cpu_num = cpu_num
        self._cpu_speed = cpu_speed
        self._mem = mem
        self._mem_util = 1 - mem_free / mem

        self._cpu = self._cpu_speed * cpu_num

        instanceNames = instances[name]

        self._vms = []

        for instance in instanceNames:
            self._vms.append(Vm(rrdWrapper,instance,name,cpu_speed,startDate, endDate))

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

        LOG.error("c value %s", cValue)

        return {
            "C" : cValue / self._cpu,
            "N" : nValue / self._bandwidth,
            "M" : mValue / self._mem,
        }
