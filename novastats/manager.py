# -*- encoding: utf-8 -*-

__docformat__ = 'restructuredtext en'

import errno
import inspect
import os
import random
import signal
import sys
import time
import datetime
from collections import namedtuple
import threading

import nova.scheduler
from nova import context
from nova import flags
from nova import manager
from nova.scheduler import rpcapi
from nova.openstack.common import cfg
from nova.openstack.common import importutils
from ceilometer.openstack.common import log as logging
from nova.openstack.common import rpc
from nova.openstack.common import context
from nova.scheduler.rpcapi import SchedulerAPI
from nova import context

from ceilometer.ganglia.rpcapi import HealthMonitorNodeAPI
from dataProvider import DataProvider

from algorithms.AntColony import AntColonyAlgorithm
from algorithms.linearPrograming import LinearProgramingAlgorithm


from rrd import rrd
from rrd.rrd import RrdWrapper
from structures.host import Host
from algorithms.base import MigrationItem
from novastats.flags import MigrationParams

from rpcapi import HealthMonitorAPI

import nova.db
from nova.db.sqlalchemy import api as db_api

try:
    import nova.openstack.common.rpc as nova_rpc
except ImportError:
    # For Essex
    import nova.rpc as nova_rpc

LOG = logging.getLogger(__name__)
FLAGS = flags.FLAGS
#LOG.logger.setLevel(10)


def find(f, seq):
    """Return first item in sequence where f(item) == True."""
    for item in seq:
        if f(item):
            return item


class HealthMonitorManager(manager.Manager):
    BASE_RPC_API_VERSION = '1.0'
    RPC_API_VERSION = '1.0'

    RRD_ROOT_DIR = "/home/stack/ganglia"

#    def __init__(self, topic=None):
#        print "HelloMgr"
##        self.topic = topic


    timestamp = None
    stabilizationTimeDelta = datetime.timedelta(minutes=20)
    lock = threading.RLock()
    lock2 = threading.RLock()

    # RPC API Implementation -------------------------------------------------------------------------------------------
    def raise_alert(self, ctx=None, alert=None):
        LOG.info(alert)

        with self.lock:
            if self.STARTED:
                # Drop alert, algorithm is running.
                # TODO: Maybe alerts should be added to cyclic buffer?
                return
            else:

                # Do not check alerts because it's too early
                if self.timestamp is not None and (self.timestamp + MigrationParams.STABILIZATION_TIME_DELTA) > datetime.datetime.now():
                    LOG.info("It's too early to run algorithm. Waiting for stabilization.")
                    return

                self.STARTED = self.dataProvider.preProcessAlert(alert)
        try:

            if self.dataProvider.preProcessAlert(alert):
                if not self._is_migrating():
                    self.prepare_resource_allocation_algorithm_input(alert)
            pass
        except Exception as err:
            print "exception %s" % err
            LOG.error(err)

        with self.lock:
            self.STARTED = False

    #-------------------------------------------------------------------------------------------------------------------

    def _get_scheduler_rpc_api(self):
        if not self.scheduler_rpc_api:
            self._init_scheduler()

        return self.scheduler_rpc_api

    def _is_migrating(self):
        ctx = context.get_admin_context()

        instances = self.db.instance_get_all(ctx)

        for instance in instances:
            if instance.vm_state == 'migrating':
                LOG.error("Migration in process. Abort algorithm execution")
                return True

        return False
        #scheduler = self._get_scheduler_rpc_api()


    # Manager inherited ------------------------------------------------------------------------------------------------
    def init_host(self):

        self.topic = HealthMonitorAPI.HEALTH_MONITOR_TOPIC
        self.ctx = context.get_admin_context()
        self.ctx.read_deleted = "no"
        self.dataProvider = DataProvider(self.RRD_ROOT_DIR, self.db, self.ctx)
        self.instances = self.db.instance_get_all_by_host(self.ctx, self.host)
        self.migration_algorithm = AntColonyAlgorithm()

        self._init_monitors_connections()
        self.STARTED = False

        self.scheduler_rpc_api = None

#        self._test_rpc_call()

    def periodic_tasks(self, context, raise_on_error=False):
        pass
    #-------------------------------------------------------------------------------------------------------------------

    class MigrationSettings(object):
        block_migration=False,
        disk_over_commit=False

        def __init__(self, **kwargs):
            self.block_migration = False
            self.disk_over_commit = False
            for key in kwargs:
                setattr(self, key, kwargs[key])

    migration_settings = MigrationSettings()

#    migration_s = namedtuple("", "block_migration disk_over_commit")
#   http://stackoverflow.com/questions/11708799/any-way-to-initialize-attributes-properties-during-class-creation-in-python

    def _init_scheduler(self):

        self.scheduler_rpc_api = SchedulerAPI()

        if self.scheduler_rpc_api is None:
            LOG.error("Scheduler == None")
            raise Exception("Error during execution scheduler")

    def _init_monitors_connections(self):

        self.conn = rpc.create_connection(new=True)

        LOG.debug(_("Creating Consumer connection for Service %s") % self.topic)

        rpc_dispatcher = self.create_rpc_dispatcher()

        # According to documentation fanout=True => broadcast to all services.
        self.conn.create_consumer(self.topic, self, fanout=True)

        # Consume from all consumers in a thread
        self.conn.consume_in_thread()

    def prepare_resource_allocation_algorithm_input(self, alert):
        """
            Hostname is virtual machine's hostname (name)
        :return:
        """

        hosts = self.dataProvider.getData().values()
        virtualMachines = []

        now = datetime.datetime.now()

        for host in hosts:
            LOG.error("stat [%s] host %s\t %s", int(time.mktime(now.timetuple())), host.Hostname, host.getMetrics())
	    for vm in host._vms:
	    	LOG.error("stat [%s]vm %s\t %s", int(time.mktime(now.timetuple())), vm.InstanceName, vm.getMetrics(host))	
            virtualMachines.extend(host._vms)

        InputData = namedtuple('InputData', 'Hosts VirtualMachines Alert')
        input_data_set = InputData(Hosts=hosts, VirtualMachines=virtualMachines, Alert=alert)

        # Count used hosts and how many boundaries are violated
        usedHostsBeforeMigration = sum([host.getIsOn() for host in hosts])
        # Dictionary <host, tuple(upperBoundsViolations, lowerBoundsViolations)>
        violationsDictionaryBeforeMigration = HealthMonitorManager.count_boundaries_violations(hosts)



        #todo if alert mem
        self.dataProvider.updateWeights()

        LOG.error("Start Algorithm")
        migrationPlans = self.migration_algorithm.execute_algorithm(input_data_set)
        LOG.error("Stop Algorithm")

        assert migrationPlans is not None, "Migration plans is none"
        plan, migrations_counter = self.choose_migration_plan(migrationPlans, virtualMachines)

        # Count used hosts and how many boundaries are violated
        usedHostsAfterMigration = sum([host.getIsOn() for host in hosts])
        # Dictionary <host, tuple(upperBoundsViolations, lowerBoundsViolations)>
        violationsDictionaryAfterMigration = HealthMonitorManager.count_boundaries_violations(hosts)

        # Zysk na naruszonych granicach SLA.
        profitUpper, profitLower = HealthMonitorManager.boundaries_profit_gained(violationsDictionaryBeforeMigration, violationsDictionaryAfterMigration)

        LOG.error("stat [%s] Migration count %s", int(time.mktime(now.timetuple())), migrations_counter)
        LOG.error("stat [%s] Hosts used before %s, after %s", int(time.mktime(now.timetuple())), usedHostsBeforeMigration, usedHostsAfterMigration)

        if alert['severity'] == 2 and usedHostsAfterMigration >= usedHostsBeforeMigration:
            #todo make alert['severity'] more human readable

            LOG.error("There is no profit from migration - skip")
            return

        self.dataProvider.saveWeights()

        for mi in plan:
            LOG.error("stat [%s] migration %s@%s", int(time.mktime(now.timetuple())), mi.instance_id, mi.hostname)

        if migrations_counter != 0:
            self.execute_plan(plan)

            #Timestamp
            self.timestamp = datetime.datetime.now()

        pass

    @staticmethod
    def count_boundaries_violations(hosts):

        def count_true(dictionary):
            assert isinstance(dictionary, dict)

            def raise_exception_missing_key(key):
                if not dictionary.has_key('C'):
                    LOG.error("Missing C key")
                    raise Exception("Missing C key")

            raise_exception_missing_key("C")
            raise_exception_missing_key("N")
            raise_exception_missing_key("M")

            true_counter = 0

            if dictionary["C"]:
                true_counter+=1

            if dictionary["N"]:
                true_counter+=1

            if dictionary["M"]:
                true_counter+=1

            return true_counter

        violations = {}

        for host in hosts:
            assert isinstance(host, Host)
            upperBoundsWithRaise = count_true(host.getUpperBounds())
            upperBoundsViolations = sum(int(violation) for violation in host.getUpperBounds().values())

            assert upperBoundsWithRaise == upperBoundsViolations, "Upperbounds violations count error"


            lowerBoundsWithRaise = count_true(host.getLowerBounds())
            lowerBoundsViolations = sum(int(violation) for violation in host.getLowerBounds().values())

            assert lowerBoundsWithRaise == lowerBoundsViolations, "Lowerbounds violations count error"

            violations[host] = (upperBoundsViolations, lowerBoundsViolations)

        return violations

    @staticmethod
    def boundaries_profit_gained(violationsBefore, violationsAfter):

        assert isinstance(violationsBefore, dict)
        assert isinstance(violationsAfter, dict)
        assert len(violationsBefore.keys()) == len(violationsAfter.keys())

        def sum_list_of_tuples(tuples):

            sumX, sumY = 0, 0
            for x,y in tuples:
                sumX+=x
                sumY+=y

            return sumX, sumY

        def profitFunctionSumWholeViolations():
            """
                Prosta funkcaj zliczająca ilość naruszeń na górnych granicach i dolnych granicach w sumie w całym środowisku

                Jeśli suma naruszeń górnych granic jest większa niż
            """

            upperViolatedBefore, lowerViolatedBefore = sum_list_of_tuples(violationsBefore.values())
            upperViolatedAfter, lowerViolatedAfter = sum_list_of_tuples(violationsAfter.values())

            # ProfitUpper - int
            # profitUpper==0 : no difference
            # profitUpper <0 : Not good
            # profitUpper >0 : Great we have less violations
            profitUpper = upperViolatedBefore - upperViolatedAfter

            # ProfitLower - int
            # profitLower==0 : no difference
            # profitLower <0 : Not good
            # profitLower >0 : Great we have less violations
            profitLower = lowerViolatedBefore - lowerViolatedAfter

            return profitUpper, profitLower

        profitUpper, profitLower = profitFunctionSumWholeViolations()

        return profitUpper, profitLower


    def choose_migration_plan(self, migrationPlans, virtualMachines):

        plan = None
	
        if migrationPlans:
            plan = migrationPlans[0]
        else:
            LOG.info("There is no migration plans")
            return (None, None)


        migrationCount = 0
        selfMigrations = []

#        print "vms"
#        for vm in virtualMachines:
#            print vm.InstanceName
#
#        print "Migration Items"
#        for item in plan:
#            print "%s@%s" % (item.instance_id, item.hostname)

	print plan

        for vm in  virtualMachines:

            assert plan is not None, "Plan is none"
            assert vm is not None, "VM is None"
            migrationItem = find(lambda migration_item: migration_item.instance_id == vm.InstanceName, plan)
            assert migrationItem is not None, "Migration item is None"

            if vm.Hostname != migrationItem.hostname:
                migrationCount+=1
                self.updateHostVmConn(vm, migrationItem)
            else:
                selfMigrations.append(migrationItem)

        for mi in selfMigrations:
            plan.remove(mi)

        return plan, migrationCount


    def updateHostVmConn(self, vm, migrationItem):

        assert self.dataProvider.hosts.has_key(migrationItem.hostname), 'data provider has no host specified in migration item'
        assert self.dataProvider.hosts.has_key(vm.Hostname), 'data provider has no host specified in vm'

        hostFrom = self.dataProvider.hosts[vm.Hostname]
        hosTo = self.dataProvider.hosts[migrationItem.hostname]

        hostFrom._vms.remove(vm)
        hosTo._vms.append(vm)




    def execute_plan(self, plan):
        """
        Executes migration plan. Migrate VMs to given nodes.
        :param migrationPlans: list
        :return:
        """

        try:
            if not self.scheduler_rpc_api:
                self._init_scheduler()

#            assert isinstance(migrationPlans, list)
#            if migrationPlans:
#                plan = migrationPlans[0]
#            else:
#                LOG.info("There is no migration plans")
#                return

            ctx = context.get_admin_context()
            instances = self.db.instance_get_all(self.ctx)

            for migrationItem in plan:
                assert isinstance(migrationItem, MigrationItem)
                #if 0:self.db=db_api # Stupid hack for code completion in ide

                instance = self._get_instance(migrationItem.instance_id, instances)
                assert instance is not None

                if instance['host'] == migrationItem.hostname:
                    continue

                migration_status = self.scheduler_rpc_api.live_migration(ctxt=ctx,
                        block_migration=self.migration_settings.block_migration,
                        disk_over_commit=self.migration_settings.disk_over_commit,
                        instance=instance,
                        dest=migrationItem.hostname)

        except:
            raise

    def _get_instance(self, name, instances):
        for instance in instances:
            if instance.name == name:
                return instance



    def collect_data(self, hostname, vm_name, resource):
        """
            Collect historical data about resource utilization for given node (hostname/virtual machine).

            CUrrently it's implemented to retrieve data from RRD's files.
        :return:
        """

        #node_topic = '%s.%s' % (HealthMonitorNodeAPI.HEALTH_MONITOR_NODE_TOPIC, hostname)

        if self.local_storage is None:
            self.local_storage = RrdWrapper(self.RRD_ROOT_DIR)

        node = "%s.%s" % (hostname, vm_name)

        endTime = datetime.datetime.now()
        startTime = endTime - datetime.timedelta(hours=1) # TODO: Move to configuration file customizable timedelta

        self.local_storage.query(startTime, endTime, resource, node)

        return None

    def collect_data_remote(self, hostname, vm_name, resource):
        """
            Collect data from network (AMQP). Not Implemented
        :param hostname:
        :param vm_name:
        :param resource:
        :return:
        """
        raise NotImplemented

        health_rpc_api = HealthMonitorNodeAPI(hostname)

        if health_rpc_api is None:
            raise Exception("Unable to get health_monitor_node RPC API object")

        message = {"resource" : resource, "vm_name": vm_name}

        return health_rpc_api.collect_recent_stats(self.ctx, message)


    def _test_rpc_call(self):

        health_monitor_node_rpc_api = HealthMonitorNodeAPI(self.host)
        message = {"resource" : "RAM", "vm_name": "SEMY"}

        result = health_monitor_node_rpc_api.collect_recent_stats(self.ctx, message)
        LOG.info("Received: %s" % result)



    def test_migration(self):
        """
        Executes migration plan. Migrate VMs to given nodes.
        :param migrationPlans: list
        :return:
        """

        instance_uuid = "3974a5b5-39d4-4bcf-a12d-a1a17bdf2341"
        hostname = "lab-os-1"

        if not self.scheduler_rpc_api:
            self._init_scheduler()


        ctx = context.get_admin_context()

        if 0:self.db=db_api # Stupid hack for code completion in ide

#        self.db.instance_get_by_uuid(self.ctx, instance_uuid)
        instances = self.db.instance_get_all(ctx)

        selected = None

        assert isinstance(instance, nova.db.sqlalchemy.models.Instance)



#        migration_status = self.scheduler_rpc_api.live_migration(ctxt=ctx,
#                                                                 block_migration=self.migration_settings.block_migration,
#                                                                 disk_over_commit=self.migration_settings.disk_over_commit,
#                                                                 instance=instance,
#                                                                 dest=hostname)

        LOG.error("Migration status %s" % migration_status)
