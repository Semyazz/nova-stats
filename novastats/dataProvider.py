__author__ = 'michal'

import datetime
from structures.host import Host
from structures.vm import Vm
from rrd.rrd import RrdWrapper
from ceilometer.openstack.common import log
import time
from rrd import rrd


LOG = log.getLogger(__name__)

class DataProvider(object):

    def __init__(self, rootDir, db, ctx):
        self.local_storage = RrdWrapper(rootDir)
        self.database = db
        self.context = ctx
        self.virtualMachines = {}
        self.estimatedMem = {}
        self.now = None
        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(hours=24)
        self.hosts = {}



    def getData(self):
        self.now = endTime = datetime.datetime.now()

        hostNames = self.local_storage.get_hosts_names()

        self.hosts = {}

        for hostName in hostNames:

            db_instances = self.database.instance_get_all_by_host(self.context, hostName) # From DB
            db_instnaces_names = [instance.name for instance in db_instances]

            try:
                cpu_idle = self.getWeightedAverageData(endTime, "cpu_idle", hostName)
                cpu_system = self.getWeightedAverageData(endTime, "cpu_system", hostName)
                cpu_num = self.getSingleValue(endTime, "cpu_num", hostName)
                cpu_speed = self.getSingleValue(endTime, "cpu_speed", hostName)
                mem = self.getSingleValue(endTime, "mem_total", hostName)
                mem_free = self.getWeightedAverageData(endTime, "mem_free", hostName)

            except Exception as err:
                LOG.error("error during retrieving host: %s data from rrd files: %s", hostName, err)
                continue

            host = Host(
                hostName,
                cpu_idle,
                cpu_system,
                cpu_num,
                cpu_speed,
                mem,
                mem_free)

            vms = []

            for instanceName in db_instnaces_names:

                vm = self.createVm(hostName, instanceName, cpu_speed, endTime)

                if vm is not None:
                    vms.append(vm)

            host._vms = vms

            host.setVmMem()

            self.hosts[hostName] = host

        return self.hosts


    def createVm(self, hostName, instanceName, hostCpuSpeed, endTime):

        try:
            cpu_util = self.getWeightedAverageData(endTime, "vcpu_util", hostName, instanceName)
            cpu_num = self.getSingleValue(endTime, "vcpu_num", hostName, instanceName)
            pkts_in = self.getWeightedAverageData(endTime, "vpkts_in", hostName, instanceName)
            pkts_out = self.getWeightedAverageData(endTime, "vpkts_out", hostName, instanceName)
            mem_declared = self.getSingleValue(endTime, "vmem_total", hostName, instanceName)

            vm = Vm(
                hostName,
                instanceName,
                cpu_util,
                cpu_num,
                pkts_in,
                pkts_out,
                mem_declared,
                hostCpuSpeed)


            if self.virtualMachines.has_key(instanceName):
                vm.setWeights(self.virtualMachines[instanceName])
            else:
                vm.setWeights(None)

            return vm

        except Exception as err:
            LOG.error("error during retrieving vm: %s data on host %s from rrd files: %s",
                instanceName,
                hostName,
                err)

            return None


    def saveWeights(self):
	
        self.lastUpdateTime = datetime.datetime.now()

        self.estimatedMem = {}

        for host in self.hosts.values():

            for vm in host._vms:
                self.estimatedMem[vm.InstanceName] = vm._mem
                LOG.error("stat [%s] instance: %s mem: %s", int(time.mktime(self.lastUpdateTime.timetuple())), vm.InstanceName, vm._mem)

    def updateWeights(self):
	
        if self.lastUpdateTime + datetime.timedelta(minutes=20) >= self.now:
            self.virtualMachines = {}

            for host in self.hosts.values():
	        
                for vm in host._vms:

                    if self.estimatedMem.has_key(vm.InstanceName):
				
                        estimatedMem = self.estimatedMem[vm.InstanceName]
                        assert estimatedMem != 0, "estimated mem is 0"

                        LOG.error("estimated mem %s %s", estimatedMem, vm._mem)

                        dif = vm._mem / estimatedMem

                        #todo think what you're doing

                        for vm in host._vms:
                            vm.modifyM(dif)
                            self.virtualMachines[vm.InstanceName] = vm.getWeights()
                            LOG.error("stat [%s] instance: %s weights: %s", int(time.mktime(self.lastUpdateTime.timetuple())), vm.InstanceName, self.virtualMachines[vm.InstanceName])

        else:
            LOG.error('Last update to long time ago - do not update weights')


    def preProcessAlert(self, alert):

        try:
            counter = alert["value"]
            metricName = counter[1]
            hostName = counter[9]["host"]
            util = None

            now = datetime.datetime.now()

            startTime = now - datetime.timedelta(minutes=5)

            db_instances = self.database.instance_get_all_by_host(self.context, hostName) # From DB

            if len(db_instances) == 0:
                #check if there are any VMs running on this host
                return

            if metricName == 'mem_util':

                memFree = self.local_storage.query(startTime, now, "mem_free", hostname = hostName).Average
                memTotal = self.getSingleValue(now, "mem_total", hostName)

                util = (1 - memFree / memTotal) * 100

            elif metricName == 'cpu_util':

                cpu_idel = self.local_storage.query(startTime, now, "cpu_idle", hostname = hostName).Average

                util = 100 - float(cpu_idle)

            elif metricName == 'pkts':

                pkts_out = self.local_storage.query(startTime, now, "pkts_out", hostname = hostName).Average
                pkts_in = self.local_storage.query(startTime, now, "pkts_in", hostname = hostName).Average

                util = (pkts_out + pkts_in) * 500.0 / 10485760 * 100

            LOG.error("stat [%s] dataProvider host: %s %s util is %s", int(time.mktime(now.timetuple())),  hostName, metricName, util)

            if util is not None and (util > 85 or util < 40):
                LOG.error("Trigger migration algorithm")
                return True
            else:
                return False

        except Exception as err:
            LOG.error("dataProvider preProcessAlert Exception %s", err)

    def getWeightedAverageData(self, endTime, metric, host, instance=None):

        startTime = endTime - datetime.timedelta(minutes=5)

        _5minuteData = self.local_storage.query(startTime, endTime, metric, instance, host)

        startTime = endTime - datetime.timedelta(minutes=10)

        _10minuteData = self.local_storage.query(startTime, endTime, metric, instance, host)

        startTime = endTime - datetime.timedelta(minutes=15)

        _15minuteData = self.local_storage.query(startTime, endTime, metric, instance, host)

        startTime = endTime - datetime.timedelta(minutes=30)

        _30minuteData = self.local_storage.query(startTime, endTime, metric, instance, host)

        return 0.4 * _5minuteData.Average +\
               0.3 * _10minuteData.Average +\
               0.2 * _15minuteData.Average +\
               0.1 * _30minuteData.Average

    def getSingleValue(self, endTime, metric, host, instance=None):

        startTime = endTime - datetime.timedelta(minutes=1)

        result = self.local_storage.query(startTime, endTime, metric, instance, host)

        return result.getLastSingleValue()


