import abc
import pulp
from pulp.solvers import GLPK



from novastats.structures.host import Host
from novastats.structures.vm import Vm

class LinearProgramingAlgorithm(object):

    def execute_algorithm(self, input_data_set):

        hosts = input_data_set.Hosts
        vms = input_data_set.VirtualMachines
        alert = input_data_set.Alert

        prob = pulp.LpProblem("test",pulp.LpMinimize)

        #if 1 host is enabled
        u = []

        x = []

        for host in hosts:

            ulp = pulp.LpVariable("used: %s" % host.Hostname,0,1,'Integer')

            u.append(ulp)

            innerX = []
            x.append(innerX)

            n = []
            m = []
            c = []

            for vm in vms:
                values = vm.getMetrics(host) #todo optimization

                lpVar = pulp.LpVariable("host %s contains %s" % (vm.InstanceName, host.Hostname),0,1,'Integer')
                innerX.append(lpVar)

                prob += ulp >= lpVar

                c.append([lpVar,values["C"]])
                n.append([lpVar,values["N"]])
                m.append([lpVar,values["M"]])

            prob += (pulp.LpAffineExpression(c) <= 1)
            prob += (pulp.LpAffineExpression(n) <= 1)
            prob += (pulp.LpAffineExpression(m) <= 1)


        #every vm on only one host
        for i in range(len(vms)):

            lps = [item[i] for item in x]
            prob += (pulp.lpSum(lps) == 1)


        prob += pulp.lpSum(u)
        GLPK().solve(prob)

        for v in prob.variables():
            print v.name, "=", v.varValue





    def create_migration_plans(self, input_data_set):
        pass

    def get_migration_plans(self):
        pass
