__author__ = 'michal'

from ceilometer.openstack.common import log
from vm import Vm
from novastats.rrd import rrd
from novastats.flags import Boundaries

LOG = log.getLogger(__name__)

class Host(object):

    def _get_last(self, list):

        return list[len(list) - 1]

    def __init__(self,
                 name,
                 cpu_system,
                 cpu_user,
                 cpu_num,
                 cpu_speed,
                 mem,
                 mem_free):

        self.Hostname = name

        LOG.error("host: %s\t"
                  "cpu_system %s\t"
                  "cpu_user %s\t"
                  "cpu_num %s\t"
                  "cpu_speed %s\t"
                  "mem %s\t"
                  "mem_free %s",
            name,
            cpu_system,
            cpu_user,
            cpu_num,
            cpu_speed,
            mem,
            mem_free)

        self._bandwidth = 10480
        self._cpu_util = cpu_user + cpu_system
        self._cpu_num = cpu_num
        self._cpu_speed = cpu_speed
        self._mem = mem
        self._mem_util = 1.0 - (float(mem_free) / float(mem))

        self._cpu = self._cpu_speed * cpu_num

        self._vms = []

    def getMWeightSum(self):
        m_weight_sum = 0

        for vmi in self._vms:
            m_weight_sum += vmi.getMWeight(self)

        return m_weight_sum


    def getMetrics(self):

        vmValues = [vmi.getValues() for vmi in self._vms]

        cValue = 0.0
        nValue = 0.0
        mValue = 0.0

        #LOG.error("values %s", vmValues)

        for vmValue in vmValues:
            cValue += vmValue["C"]
            nValue += vmValue["N"]
            mValue += vmValue["M"]

        #LOG.error("c value %s", cValue)

        return {
            "C" : float(cValue) / float(self._cpu),
            "N" : float(nValue) / float(self._bandwidth),
            "M" : float(mValue) / float(self._mem),
        }

    def setVmMem(self):
        mWeightSum = self.getMWeightSum()

        for vmi in self._vms:
            vmi.setMem(self, mWeightSum)

    def getReservedSpace(self):
        return (1.0 - Boundaries.CPU_UPPER_BOUND,
                1.0 - Boundaries.NETWORK_UPPER_BOUND,
                1.0 - Boundaries.MEMORY_UPPER_BOUND)

    def getUpperBounds(self):

        metrics = self.getMetrics()

        return {
            "C" : metrics["C"] > Boundaries.CPU_UPPER_BOUND,
            "N" : metrics["N"] > Boundaries.NETWORK_UPPER_BOUND,
            "M" : metrics["M"] > Boundaries.MEMORY_UPPER_BOUND,
        }

    def getLowerBounds(self):

        metrics = self.getMetrics()

        return {
            "C" : metrics["C"] < Boundaries.CPU_LOWER_BOUND,
            "N" : metrics["N"] < Boundaries.NETWORK_LOWER_BOUND,
            "M" : metrics["M"] < Boundaries.MEMORY_LOWER_BOUND,
        }

    def getIsOn(self):
        return len(self._vms) > 0
