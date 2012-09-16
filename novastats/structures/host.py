__author__ = 'michal'

from ceilometer.openstack.common import log
from vm import Vm


LOG = log.getLogger(__name__)

class Host(object):

    def _get_last(self, list):

        return list[len(list) - 1]

    def __init__(self, rrdWrapper, instances, name, startDate, endDate):

        self.Hostname = name

        cpu_system = rrdWrapper.query(startDate, endDate, "cpu_system", hostname = name).Average
        cpu_user = rrdWrapper.query(startDate, endDate, "cpu_user", hostname = name).Average
        cpu_num = rrdWrapper.query(startDate, endDate, "cpu_num", hostname = name).getLastSingleValue()
        cpu_speed = rrdWrapper.query(startDate, endDate, "cpu_speed", hostname = name).getLastSingleValue()
        mem = rrdWrapper.query(startDate, endDate, "mem_total", hostname = name).getLastSingleValue()
        mem_free = rrdWrapper.query(startDate, endDate, "mem_free", hostname = name).Average


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
        self._mem_util = 1 - mem_free / mem

        self._cpu = self._cpu_speed * cpu_num

        self._vms = []

        for instance in instances:
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

        #LOG.error("values %s", vmValues)

        for vmValue in vmValues:
            cValue += vmValue["C"]
            nValue += vmValue["N"]
            mValue += vmValue["M"]

        #LOG.error("c value %s", cValue)

        return {
            "C" : cValue / self._cpu,
            "N" : nValue / self._bandwidth,
            "M" : mValue / self._mem,
        }
