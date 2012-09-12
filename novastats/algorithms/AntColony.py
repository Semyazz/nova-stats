__author__ = 'semy'

from base import AlgorithmBase
from collections import namedtuple
from novastats.structures.host import Host
from novastats.structures.host import Vm

class SimpleBackpackAlgorithm(AlgorithmBase):


    class Capacity(object):

        def __init__(self, memory, network, cpu):
            self.Memory = memory
            self.Network = network
            self.CPU = cpu

    def execute_algorithm(self, input_data_set):
        """
            Bin packing Algorithm
        """

        hosts = input_data_set.Hosts
        vms = input_data_set.VirtualMachines
        alert = input_data_set.Alert

        # Ant Colony Algorithm
        Bins = hosts
        Items = vms

        assert isinstance(Bins, list)
        assert isinstance(Items, list)

        nCycles = 2
        nAnts = 5

        C = dict()
        I = dict()
        Binit = dict()

        for bin in Bins:
            assert isinstance(bin, Host)
            C[bin] = self.Capacity(memory=bin._mem, network=bin._bandwidth, cpu=100)
            Binit[bin] = self.Capacity(memory=0, network=0, cpu=0)

        for item in Items:
            assert isinstance(item, Vm)
            I[item] = self.Capacity(memory=item._mem_declared, network=item._bandwidth, cpu=item._cpu_util)

        n = len(Bins)
        m = len(Items)

        S = dict()

        for q in range(0, nCycles-1):
            for a in range(0, nAnts):
                B = Binit.copy()
                IS = list(Items)
                v = Bins.__iter__().next()
                S[a] = self._initZeroS(m, n)

                try:
                    while len(IS) != 0:
                        N[v] = self.selectItems(C[v], B[v], IS, I)
                        if len(N[v]) != 0:

                            # Choose item stochastically

                            i = None
                            S[Items.index(i)][Bins.index(v)] = 1

                            IS.remove(i)
                            B[v] = self._sumCapacityVectors(B[v], I[i])
                        else:
                            v = Bins.__iter__().next()

                except StopIteration as stop:
                    pass







        pass


    def selectItems(self, hostCapacity, hostUsed, instances, instancesResourcesDemands):

        selected = []

        for instance in instances:
            demands = instancesResourcesDemands[instance]

            requirements = self._sumCapacityVectors(demands, hostUsed)

            if self._lessEqualCapacityVector(requirements, hostCapacity):
                selected.append(instance)

        return selected

    def _sumCapacityVectors(self, v1, v2):

        assert isinstance(v1, self.Capacity)
        assert isinstance(v2, self.Capacity)

        return Capacity(memory=v1.Memory + v2.Memory,
                network=v1.Network + v2.Network,
                cpu=v1.CPU + v2.CPU)

    def _lessEqualCapacityVector(self, v1, v2):

        cpu = v1.CPU <= v2.CPU
        memory = v1.Memory <= v2.Memory
        network = v1.Network <= v1.Network

        return cpu and memory and network

    def _initZeroS(self, m, n):
        S = [][]

        for row in range(0, m-1):
            for column in range(0, n-1):
                S[row][column] = 0

        return S

    def create_migration_plans(self, input_data_set):

        plans = list()

        def append_recipe(vm_hostname, hostname_from, hostname_to):
            plans.append(dict(vm = vm_hostname, host_from = hostname_from, host_to = hostname_to))

        self.append_method = append_recipe

        self.execute_algorithm(input_data_set)

        return plans