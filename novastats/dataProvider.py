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
	self.virtualMachines = None
	self.estimatedMem = {}


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

        return self.hosts

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

            if self.estimatedMem.has_key(host.Hostname):
	    	estimatedMem = self.estimatedMem[host.Hostname]

            	dif = hostMem - (estimatedMem / host._mem)

            #todo think what you're doing

            	for vm in host._vms:
                    vm.modifyM(dif)






