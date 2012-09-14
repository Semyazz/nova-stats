__author__ = 'semy'

import math
from base import AlgorithmBase
from collections import namedtuple
from novastats.structures.host import Host
from novastats.structures.host import Vm

class AntColonyAlgorithm(AlgorithmBase):


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

        assert Items != 0
        assert Bins != 0

        assert isinstance(Bins, list)
        assert isinstance(Items, list)

        nCycles = 3 # TODO Given
        nAnts = 5 # TODO Given
        ro = 0.7 #TODO Given
        g = 2.0 # TODO Given
        alfa = 1 #TODO Given
        beta = 2 # TODO Given
        tauMax = 3.0 # TODO Given
        tauMin = tauMax / g

        C = dict()
        I = dict()
        Sbest = dict()

        Binit = dict() # TMP used

        for bin in Bins:
            assert isinstance(bin, Host)
            C[bin] = self.Capacity(memory=bin._mem, network=bin._bandwidth, cpu=1)
            Binit[bin] = self.Capacity(memory=0, network=0, cpu=0)

        for item in Items:
            assert isinstance(item, Vm)
            I[item] = self.Capacity(memory=item._mem_declared, network=item._bandwidth, cpu=item._cpu_util)
            Sbest[item] = [{bin: 0} for bin in Bins]

        n = len(Bins)
        m = len(Items)

        Zeros2DArray = self._initZeroS(m, n) # TMP
        Zeros2DDict = {item : {bin: 0 for bin in Bins} for item in Items}

        S = dict()
        N = dict()
        tau = dict()
        for bin in Bins:
            tauItem = dict()
            for item in Items:
                tauItem[item] = tauMax
            tau[bin] = tauItem

        eta = dict()

#        Sbest = [[0 for _ in range(n)] for _ in range(m)]


        assert len(Sbest) == m
        assert len(Sbest[Items[0]]) == n
        # Solution matrix

        for q in range(0, nCycles-1):
            for a in range(0, nAnts):
                B = Binit.copy()
                IS = list(Items)
                v = Bins.__iter__().next()
                S[a] = Zeros2DDict.copy()

                assert len(S[a]) == m
                assert len(S[a][Items[0]]) == n

                try:
                    while len(IS):
                        N[v] = self.selectItems(C[v], B[v], IS, I)
                        etas = self.computeEta(C[v], B[v], I)
                        if len(N[v]):

                            # Choose item stochastically
                            p = self.computeProbabilities(N[v], tau[v], etas, alfa, beta)
                            assert sum(p.values()) == 1
                            i = self.chooseItemStochastically(p)
                            assert i in N[v]

                            S[a][i][v] = 1

                            IS.remove(i)
                            B[v] = self._sumCapacityVectors(B[v], I[i])
                        else:
                            v = Bins.__iter__().next()

                except StopIteration as stop:
                    pass


            if q == 0:
                Sbest, deltaTau = self.saveBest(S, Sbest, m, n)
                print "q == 0"
            else:
                Sbest, deltaTau = self.isGlobalBest(S, Sbest, m, n)

            # Compute tauMin and tauMax

            for bin in Bins:
                for item in Items:
                    tau[bin][item] = (1 - ro) * tau[bin][item] + deltaTau[item][bin]
                    if tau[bin][item] > tauMax:
                        tau[bin][item] = tauMax
                    if tau[bin][item] < tauMin:
                        tau[bin][item] = tauMin

        print Sbest


    def computeEta(self, c, b, I):

        etas = dict()
        for k,r in I.items():
            etas[k] = self._l1norm(self._differenceCapacityVectors(c, self._sumCapacityVectors(b, r)))

        return etas

    def _l1norm(self, v):

        assert isinstance(v, self.Capacity)

        return v.CPU + v.Memory + v.Network

    def computeDeltaTau(self, S, min_used_bins):
        deltaTau = dict()

        objCounter = 0
        expected = len(S) * len(S[S.keys()[0]])

        for item, bins in S.items():
            assert len(bins) == 3
            deltaTau[item] = dict()
            for bin, value in bins.items():
                if value == 1:
                    deltaTau[item][bin] = 1.0 / min_used_bins
                else:
                    deltaTau[item][bin] = 0.0

        return deltaTau

    @staticmethod
    def usedBins(S):
        used_bins_number = dict()

        for item, bins in S.items():
            for bin, value in bins.items():
                if not used_bins_number.has_key(bin):
                    used_bins_number[bin] = 0

                used_bins_number[bin] = used_bins_number[bin] or value

        return sum(used_bins_number.values())


    def saveBestOrIsGlobalBest(self, S, Sbest):

        if not Sbest:
            print "Select first"
            Sbest = S[0]

        min_used_bins = AntColonyAlgorithm.usedBins(Sbest)

        for key, Sant in S.items():
            used_bins_number = AntColonyAlgorithm.usedBins(Sant)
            if min_used_bins > used_bins_number:
                Sbest = Sant
                min_used_bins = used_bins_number

        deltaTau = self.computeDeltaTau(Sbest, min_used_bins)

        return Sbest, deltaTau


    def chooseItemStochastically(self, probabilities):

        import random
        # From http://eli.thegreenplace.net/2010/01/22/weighted-random-generation-in-python/
        def weighted_choice(weights):
            totals = []
            running_total = 0

            for w in weights:
                running_total += w
                totals.append(running_total)

            rnd = random.random() * running_total
            for i, total in enumerate(totals):
                if rnd < total:
                    return i

        items = [len(probabilities)]
        probs = [len(probabilities)]
        i = 0
        for item, p in probabilities.items():
            items[i] = item
            probs[i] = p

        index = weighted_choice(probs)

        return items[index]


    def computeProbabilities(self, items, tau, eta, alfa, beta):

        probabilities = dict()

        def powerAndMultiply(item):
            return math.pow(tau[item], alfa) * math.pow(eta[item], beta)

        lower = reduce(lambda x,y: x+y ,[powerAndMultiply(item) for item in items])

        for item in items:
            probabilities[item] = powerAndMultiply(item)/lower

        return probabilities


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

        return self.Capacity(memory=v1.Memory + v2.Memory,
                network=v1.Network + v2.Network,
                cpu=v1.CPU + v2.CPU)

    def _differenceCapacityVectors(self, v1, v2):

        assert isinstance(v1, self.Capacity)
        assert isinstance(v2, self.Capacity)

        return self.Capacity(memory=v1.Memory - v2.Memory,
            network=v1.Network - v2.Network,
            cpu=v1.CPU - v2.CPU)

    def _lessEqualCapacityVector(self, v1, v2):

        cpu = v1.CPU <= v2.CPU
        memory = v1.Memory <= v2.Memory
        network = v1.Network <= v1.Network

        return cpu and memory and network

    def _initZeroS(self, m, n):
        S = [[0 for _ in range(n)] for _ in range(m)]

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