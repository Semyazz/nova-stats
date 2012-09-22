__author__ = 'michal'

import datetime
from structures.host import Host
from structures.vm import Vm
from rrd.rrd import RrdWrapper

class DataProvider(object):

    def __init__(self, rootDir, db, ctx):
        self.local_storage = RrdWrapper(rootDir)
        self.database = db
        self.context = ctx
        self.virtualMachines = {}
        self.estimatedMem = {}
        self.now = None
        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(hours=24)



    def getData(self):
        self.now = endTime = datetime.datetime.now()

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

        return self.hosts

    def saveWeights(self):
	
        self.lastUpdateTime = datetime.datetime.now()

        self.virtualMachines = {}
        self.estimatedMem = {}

        for host in self.hosts:

            for vm in host._vms:
                self.virtualMachines[vm.InstanceName] = vm.getWeights()
                self.estimatedMem[vm.InstanceName] = vm._mem

    def updateWeights(self):
	
        if self.lastUpdateTime + datetime.timedelta(minutes=20) >= self.now:

            for host in self.hosts:
	        
                for vm in host._vms:

                    if self.estimatedMem.has_key(vm.InstanceName):
                        estimatedMem = self.estimatedMem[vm.InstanceName]
                        assert estimatedMem != 0, "estimated mem is 0"

                        dif = vm._mem / estimatedMem

                        #todo think what you're doing

                        for vm in host._vms:
                            vm.modifyM(dif)




