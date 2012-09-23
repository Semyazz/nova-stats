__author__ = 'semy'

import math
from base import AlgorithmBase
from base import MigrationItem
from collections import namedtuple
from novastats.structures.host import Host
from novastats.structures.host import Vm


from ceilometer.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class AntColonyAlgorithm(AlgorithmBase):


    class Capacity(object):

        def __init__(self, memory, network, cpu):
            self.Memory = memory
            self.Network = network
            self.CPU = cpu

    class Solution(object):

        def __init__(self, minBins, schedule):
            self.MinBins = minBins
            self.Schedule = schedule

    def __init__(self):
        self.Solutions = []
        self.profitFunction = None

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

        Binit = dict() # TMP used

        for bin in Bins:
            assert isinstance(bin, Host)
            C[bin] = self.Capacity(memory=1.0, network=1.0, cpu=1.0)
            c, n, m = bin.getReservedSpace()
            Binit[bin] = self.Capacity(memory=m, network=n, cpu=c)

#        for item in Items:
#            assert isinstance(item, Vm)
#            I[item] = self.Capacity(memory=item._mem_declared, network=item._bandwidth, cpu=item._cpu_util)

        n = len(Bins)
        m = len(Items)

        Zeros2DDict = {item : {bin: 0 for bin in Bins} for item in Items}

        S = dict()
        N = dict()
        tau = dict()
        for bin in Bins:
            tauItem = dict()
            for item in Items:
                tauItem[item] = tauMax
            tau[bin] = tauItem
        #eta = dict()
        #ETA computed in function

        # Solution dictionary dict<VirtualMachine, dict<Host, int>> where int => 0|1.
        Sbest = Zeros2DDict.copy()

        assert len(Sbest) == m
        assert len(Sbest[Items[0]]) == n
        # Solution matrix

        # Ant
        for q in range(0, nCycles-1):
            for a in range(0, nAnts):

                # Host's used resources in terms of Capacity class [Memory, Network, CPU]
                # Increased during algorithm
                # Binit == Initialization Capacity(Memory=0, Network=0, CPU=0)
                B = Binit.copy()

                # List of items to schedule.
                IS = list(Items)

                # Ant's solution. type(S[a]) == type(Sbest)
                # Ant's are numbered 0..nAnts.
                S[a] = Zeros2DDict.copy()

                assert len(S[a]) == m
                assert len(S[a][Items[0]]) == n

                iterator = Bins.__iter__()
                # First Bin (Host)
                v = iterator.next()

                I = self._get_instances_vectors(v, Items)

                try:
                    while len(IS):

                        # Items (VirtualMachines) which can be put into bin
                        N[v] = self.selectItems(C[v], B[v], IS, I)

                        if len(N[v]):
                            etas = self.computeEta(C[v], B[v], I)

                            # Compute probabilities for each Item (VirtualMachine).
                            # type(p) == dict<VirtualMachine, float>
                            p = self.computeProbabilities(N[v], tau[v], etas, alfa, beta)

                            # Total probability ~== 1.0
                            assert  abs(sum(p.values()) - 1.0) < 1e-6, "probability sum: %s" % (sum(p.values()))

                            # Weighted random choose
                            # TODO: There are faster algorithms to do that than that implemented in chooseItemStochastically
                            # i == VirtualMachine which will be put into bin
                            i = self.chooseItemStochastically(p)

                            assert i in N[v]

                            # Put Instance i into Bin v.
                            S[a][i][v] = 1

                            # Remove instance from instances to schedule
                            IS.remove(i)

                            # Update Host's used resources
                            B[v] = self._sumCapacityVectors(B[v], I[i])
                        else:
                            guard = v
                            v = iterator.next()
                            assert guard is not v
                            I = self._get_instances_vectors(v, Items)

                except StopIteration as stop:
                    pass


            # Update best solution. Choose best one from ants' solutions
            # Compute deltaTau
            if q == 0:
                Sbest, deltaTau = self.saveBestOrIsGlobalBest(S, Sbest)
            else:
                Sbest, deltaTau = self.saveBestOrIsGlobalBest(S, Sbest)

            # Compute tauMin and tauMax
            for bin in Bins:
                for item in Items:
                    tau[bin][item] = (1 - ro) * tau[bin][item] + deltaTau[item][bin]
                    if tau[bin][item] > tauMax:
                        tau[bin][item] = tauMax
                    if tau[bin][item] < tauMin:
                        tau[bin][item] = tauMin

        self.print_result(Sbest)

        return [self.get_solution(Sbest)]

    def get_solution(self, solution_matrix):

        migration_plan = []

        for virtual_machine, hosts in solution_matrix.items():
            for host, value in hosts.items():
                if value == 1:
                    migrationItem = MigrationItem(virtual_machine, host)
                    migration_plan.append(migrationItem)

        return migration_plan


    def _get_instances_vectors(self, host, instances):

        I = dict()

        for instance in instances:
            assert isinstance(instance, Vm)
            metrics = instance.getMetrics(host)
            I[instance] = self.Capacity(memory=metrics["M"], network=metrics["N"], cpu=metrics["C"])
            cap = I[instance]
            #assert isinstance(cap, self.Capacity)
            #LOG.error("I:%s\tCPU:%s\tMem:%s\tNet:%s" % (instance.InstanceName, cap.CPU, cap.Memory, cap.Network))

        return I

    def print_result(self, Sbest):

        for item, bins in Sbest.items():
            for bin, value in bins.items():
                if value == 1:
                    print "Instance %s@%s" % (item.InstanceName, bin.Hostname)

    def computeEta(self, c, b, I):

        etas = dict()
        for k,r in I.items():
            etas[k] = self._l1norm(self._differenceCapacityVectors(c, self._sumCapacityVectors(b, r)))

        return etas

    def _l1norm(self, v):
        """
            Compute L1-Norm. Simple just sum whole vector
        """

        assert isinstance(v, self.Capacity)

        return v.CPU + v.Memory + v.Network

    def computeDeltaTau(self, S, min_used_bins):
        deltaTau = dict()

        for item, bins in S.items():
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


    def profitFunction(self, S, Sbest):
        pass

    def saveBestOrIsGlobalBest(self, S, Sbest):

        if self.profitFunction:
            # SBest - current SBest
            # Solutions
            Sbest = self.profitFunction(S, SBest)
            min_used_bins = AntColonyAlgorithm.usedBins(Sbest)
        else:
            min_used_bins = AntColonyAlgorithm.usedBins(Sbest)

            if min_used_bins == 0:
                Sbest = S[0]

            for key, Sant in S.items():
                used_bins_number = AntColonyAlgorithm.usedBins(Sant)
                if min_used_bins > used_bins_number:
                    Sbest = Sant
                    min_used_bins = used_bins_number
                    self.Solutions = [self.Solution(min_used_bins, Sbest)]
                elif min_used_bins == used_bins_number:
                    self.Solutions.append(self.Solution(min_used_bins, Sant))

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
    
    def get_migration_plans(self):
	    pass
