__author__ = 'semy'


from novastats.algorithms.AntColony import AntColonyAlgorithm
from nova import test
from collections import namedtuple

from novastats.structures.host import Host
from novastats.structures.vm import Vm
from novastats.manager import HealthMonitorManager

import mox


def MockHostList():

    h1 = Host("Host1", 50, 0, 4, 1000, 8192, 2*8192/8) # 2*1GB free
    h2 = Host("Host2", 25, 0, 4, 1000, 8192, 2*8192/8) # 2*1GB free
    h3 = Host("Host3", 0, 0, 4, 1000, 8192, 4*8192/8)  # 4*1GB free
    h4 = Host("Host4", 0, 0, 4, 1000, 8192, 4*8192/8)  # 4*1GB free

    vm1 = Vm(h1.Hostname, "vm1", 100, 1, 0, 0, 2048, 1000)
    vm1.setWeights(None)

    vm2 = Vm(h1.Hostname, "vm2", 50, 2, 0, 0, 4096, 1000)
    vm2.setWeights(None)

    vm3 = Vm(h2.Hostname, "vm3", 25, 4, 0, 0, 4096, 1000)
    vm3.setWeights(None)

    vm4 = Vm(h3.Hostname, "vm4", 0, 1, 0, 0, 4096, 1000)
    vm4.setWeights(None)

    vm5 = Vm(h4.Hostname, "vm5", 0, 1, 0, 0, 4096, 1000)
    vm5.setWeights(None)

    h1._vms = [vm1, vm2]
    h1.setVmMem()

    h2._vms = [vm3]
    h2.setVmMem()

    h3._vms = [vm4]
    h3.setVmMem()

    h4._vms = [vm5]
    h4.setVmMem()


    return [h1, h2, h3, h4]


class TestManager(test.TestCase):

    def setUp(self):
        super(TestManager, self).setUp()



    def test_count_boundaries_violations(self):

        hosts = MockHostList()

        for host in hosts:
            print host.Hostname
            print "\tUpper %s\n\tLower %s" % (host.getUpperBounds(), host.getLowerBounds())

        violationsDictionaryBefore = HealthMonitorManager.count_boundaries_violations(hosts)

        for k, v in violationsDictionaryBefore.iteritems():
            print "%s: %s" % (k.Hostname, v)


        h1 = hosts[0]
        h2 = hosts[1]
        h3 = hosts[2]
        h4 = hosts[3]

        vm1 = h1._vms[0]
        vm2 = h1._vms[1]
        vm3 = h2._vms[0]
        vm4 = h3._vms[0]
        vm5 = h4._vms[0]

        h1._vms.remove(vm2)
        h2._vms.append(vm2)

        print "After migration\n"

        for host in hosts:
            print host.Hostname
            print "\tUpper %s\n\tLower %s" % (host.getUpperBounds(), host.getLowerBounds())

        violationsDictionaryAfter = HealthMonitorManager.count_boundaries_violations(hosts)

        for k, v in violationsDictionaryAfter.iteritems():
            print "%s: %s" % (k.Hostname, v)


        profitUpper, profitLower = HealthMonitorManager.boundaries_profit_gained(violationsDictionaryBefore, violationsDictionaryAfter)

        print "Profit Upper: %s, Lower: %s" % (profitUpper, profitLower)