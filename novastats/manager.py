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

        hosts = self.dataProvider.getData()
        virtualMachines = []

        for host in hosts:
            LOG.error("host %s\t %s", host.Hostname, host.getMetrics())
            virtualMachines.extend(host._vms)

#        collectedData = self.collect_data(hostname, vm_name, resource)
#        physicalNodes = self.get_physical_nodes_resources_utilization()

#        input_data_set = dict(resources_history=collectedData, virtual_machines=virtualMachines, physical_nodes=physicalNodes)
#
        InputData = namedtuple('InputData', 'Hosts VirtualMachines Alert')
        input_data_set = InputData(Hosts=hosts, VirtualMachines=virtualMachines, Alert=alert)

		
        #todo if alert mem
        self.dataProvider.updateWeights()

        LOG.error("Start Algorithm")
#        self.test_migration()

        migrationPlans = self.migration_algorithm.execute_algorithm(input_data_set)
        LOG.error("Stop Algorithm")

        assert migrationPlans is not None, "Migration plans is none"
        #self.dataProvider.saveWeights()

        plan, migrations_counter = self.choose_migration_plan(migrationPlans, virtualMachines)
        LOG.error("Migration count %s", migrations_counter)

        for mi in plan:
            print "%s@%s" % (mi.instance_id, mi.hostname)

        if migrations_counter != 0:
            self.execute_plan(plan)
            import time
            time.sleep(60)

        import time
        time.sleep(30)

        pass

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

        for vm in  virtualMachines:

            assert plan is not None, "Plan is none"
            assert vm is not None, "VM is None"
            migrationItem = find(lambda migration_item: migration_item.instance_id == vm.InstanceName, plan)
            assert migrationItem is not None, "Migration item is None"

            if vm.Hostname != migrationItem.hostname:
                migrationCount+=1
            else:
                selfMigrations.append(migrationItem)

        for mi in selfMigrations:
            plan.remove(mi)

        return (plan, migrationCount)

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
