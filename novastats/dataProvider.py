__author__ = 'michal'

import datetime
from structures.host import Host
from structures.vm import Vm
from rrd.rrd import RrdWrapper
import math

class DataProvider(object):

    def __init__(self, rootDir, db, ctx):
        self.local_storage = RrdWrapper(rootDir)
        self.database = db
        self.context = ctx


    def getData(self):
        endTime = datetime.datetime.now()

        hostNames = self.local_storage.get_hosts_names()

        self.hosts = []

        for hostName in hostNames:

            db_instances = self.database.instance_get_all_by_host(self.context, hostName) # From DB
            db_instnaces_names = [instance.name for instance in db_instances]

            if self.virtualMachines is not None:
                host = Host(self.local_storage, db_instnaces_names, hostName, endTime, self.virtualMachines)
            else:
                host = Host(self.local_storage, db_instnaces_names, hostName, endTime)

            self.hosts.append(host)

    def saveWeights(self):

        self.virtualMachines = {}
        self.estimatedMem = {}

        for host in self.hosts:

            estimatedMem = 0

            for vm in host._vms:
                self.virtualMachines[vm.InstanceName] = vm.getWeights()
                estimatedMem += vm._mem

            self.estimatedMem[host.Hostname] = estimatedMem



    def updateWeights(self):

        for host in self.hosts:

            hostMem = host._mem_util
            estimatedMem = self.estimatedMem[host.Hostname]

            dif = math.floor(hostMem - (estimatedMem / host._mem))

            #todo think what you're doing

            if dif > 0:

                for vm in host._vms:
                    for i in rage(0,dif):
                        vm.decreaseM()

            elif dif < 0:
                dif *= -1

                for vm in host._vms:
                    for i in rage(0,dif):
                        vm.increaseM()

        self.saveWeights()





