__author__ = 'semy'

from novastats.algorithms.AntColony import AntColonyAlgorithm
from nova import test
from collections import namedtuple

from novastats.structures.host import Host
from novastats.structures.vm import Vm

import mox

class TestAntColony(test.TestCase):

    def setUp(self):
        super(TestAntColony, self).setUp()
        self.hostMocker = mox.Mox()
        self.vmMocker = mox.Mox()


    def test_algorithm(self):

        ant = AntColonyAlgorithm()

        input_data_set = namedtuple('InputData', 'Hosts VirtualMachines Alert')

        def host_init(self, memory, bandwidth):
            self._mem = memory
            self._bandwidth = bandwidth
            self._cpu = 1000

        def vm_init(self, mem_declared, bandwitch, cpu_util):
            self._mem_declared = mem_declared
            self._bandwidth = bandwitch
            self._cpu_util = cpu_util
            self._cpu_num = 1
            self._cpu_speed = 1000
            self._pkts_in = 0
            self._pkts_out = 0
            self._mem = mem_declared

        Host.__init__ = host_init
        Vm.__init__ = vm_init

        maxMem = 1024.0
        maxCPU = 100.0
        maxBandwith = 10000.0

        host1 = Host(1.0, 1.0)
        host1.Hostname = "host1"
        host2 = Host(1.0, 1.0)
        host2.Hostname = "host2"

        vm1 = Vm(512.0/maxMem, 1000.0/maxBandwith, 30.0/100.0)
        vm1.InstanceName = "instance-00001"
        vm2 = Vm(512.0/maxMem, 1000.0/maxBandwith, 30.0/100.0)
        vm2.InstanceName = "instance-00002"
        vm3 = Vm(1024.0/maxMem, 1000.0/maxBandwith, 30.0/100.0)
        vm3.InstanceName = "instance-00003"
        vm4 = Vm(512.0/maxMem, 1000.0/maxBandwith, 30.0/100.0)
        vm4.InstanceName = "instance-00004"

        input_data_set.Hosts = [host1, host2]
        input_data_set.VirtualMachines = [vm1, vm2, vm3, vm4]

        ant.execute_algorithm(input_data_set)



    def test_mocking(self):

        def host_init(self, memory, bandwidth):
            self._mem = memory
            self._bandwidth = bandwidth

        def vm_init(self, mem_declared, bandwitch, cpu_util):
            self._mem_declared = mem_declared
            self._bandwidth = bandwitch
            self._cpu_util = cpu_util

        Host.__init__ = host_init
        Vm.__init__ = vm_init

        host1 = Host(1024, 10000)
        host2 = Host(1024, 10000)

        vm1 = Vm(256, 1000, 30)
        vm2 = Vm(256, 1000, 30)

        assert isinstance(host1, Host)
        assert isinstance(host2, Host)

        assert isinstance(vm1, Vm)
        assert isinstance(vm2, Vm)