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
#FLAGS = flags.FLAGS
#LOG.logger.setLevel(10)

class HealthMonitorManager(manager.Manager):
    BASE_RPC_API_VERSION = '1.0'
    RPC_API_VERSION = '1.0'

    RRD_ROOT_DIR = "/home/stack/ganglia"

#    def __init__(self, topic=None):
#        print "HelloMgr"
##        self.topic = topic


    lock = threading.RLock()

    # RPC API Implementation -------------------------------------------------------------------------------------------
    def raise_alert(self, ctx=None, alert=None):
        LOG.info(alert)

        with self.lock:
            if self.STARTED:
                # Drop alert, algorithm is running.
                # TODO: Maybe alerts should be added to cyclic buffer?
                return
            else:
                self.STARTED = True

        try:

            print "alert %s" % alert
            counter = alert["value"]
            metricName = counter[1]
            resource_matadata = counter[9]
            hostName = resource_matadata["host"]

            LOG.error("alert %s", alert)

            util = 0
            now = datetime.datetime.now()
            startTime = now - datetime.timedelta(minutes=5)


            if metricName == 'mem_util':
                memFree = self.dataProvider.local_storage.query(startTime,
                                                                now,
                                                                "mem_free",
                                                                hostname = hostName).Average
                memTotal = rrd.getSingleValue(self.dataProvider.local_storage, now, "mem_total", alert.HostName)

                util = (1 - memFree / memTotal) * 100

            elif metricName == 'cpu_util':
                cpu_user = self.dataProvider.local_storage.query(startTime, now, "cpu_user", hostname = hostName).Average
                cpu_system = rrd.getSingleValue(self.dataProvider.local_storage, now, "cpu_system", alert.HostName)

                util = cpu_user + cpu_system

            elif metricName == 'pkts':
                pkts_out = self.dataProvider.local_storage.query(startTime, now, "pkts_out", hostname = hostName).Average
                pkts_in = rrd.getSingleValue(self.dataProvider.local_storage, now, "pkts_in", alert.HostName)

                util = pkts_out + pkts_in



            if util > 70 or util < 40:
                #hostNames = self.local_storage.get_hosts_names()
                self.prepare_resource_allocation_algorithm_input(alert)


        except Exception as err:
            print "exception %s" % err
            LOG.error(err)

        with self.lock:
            self.STARTED = False

    #-------------------------------------------------------------------------------------------------------------------


    # Manager inherited ------------------------------------------------------------------------------------------------
    def init_host(self):
        self.topic = HealthMonitorAPI.HEALTH_MONITOR_TOPIC
        self.ctx = context.get_admin_context()
        self.ctx.read_deleted = "no"
        self.instances = self.db.instance_get_all_by_host(self.ctx, self.host)
        self.migration_algorithm = AntColonyAlgorithm()

        self._init_monitors_connections()
        self.STARTED = False

        self.dataProvider = DataProvider(self.RRD_ROOT_DIR, self.db, self.ctx)



#        self._test_rpc_call()

    def periodic_tasks(self, context, raise_on_error=False):
        pass
    #-------------------------------------------------------------------------------------------------------------------

    class MigrationSettings(object):
        block_migration=None,
        disk_over_commit=None

        def __init__(self, **kwargs):
            self.block_migration = True
            self.disk_over_commit = True
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
        migrationPlans = self.migration_algorithm.create_migration_plans(input_data_set)
        LOG.error("Stop Algorithm")

        self.dataProvider.saveWeights()


        import time
        time.sleep(100)

        #self.execute_plan(migrationPlans)

        pass

    def create_migration_plans(self, input_data_set):
        #TODO
        pass


    def execute_plan(self, migrationPlans):
        """
        Executes migration plan. Migrate VMs to given nodes.
        :param migrationPlans: list
        :return:
        """
        try:
            if not self.scheduler_rpc_api:
                self._init_scheduler()

            assert isinstance(migrationPlans, list)
            if migrationPlans:
                plan = migrationPlans[0]
            else:
                LOG.info("There is no migration plans")
                return

            ctx = context.get_admin_context()
            for migrationItem in plan:
                assert isinstance(migrationItem, MigrationItem)
                if 0:self.db=db_api # Stupid hack for code completion in ide

                instance = self.db.instance_get(self.ctx, migrationItem.instance_id)
                assert isinstance(instance, nova.db.sqlalchemy.models.Instance)

                migration_status = self.scheduler_rpc_api.live_migration(ctxt=ctx,
                        block_migration=self.migration_settings.block_migration,
                        disk_over_commit=self.migration_settings.disk_over_commit,
                        instance=instance,
                        dest=migrationItem.hostname)

        except:
            raise

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


    def get_virtual_machines_locations(self):
        """
        Gets dictionary {"physical node hostname": set of virtual machines (their hostnames)}
        :return:
        """
        pass

    def get_physical_nodes_resources_utilization(self):
        pass

    def _test_rpc_call(self):

        health_monitor_node_rpc_api = HealthMonitorNodeAPI(self.host)
        message = {"resource" : "RAM", "vm_name": "SEMY"}

        result = health_monitor_node_rpc_api.collect_recent_stats(self.ctx, message)
        LOG.info("Received: %s" % result)



    def test_migration(self, migrationPlans):
        """
        Executes migration plan. Migrate VMs to given nodes.
        :param migrationPlans: list
        :return:
        """

        instance_id = ""
        hostname = ""

        if not self.scheduler_rpc_api:
            self._init_scheduler()


        ctx = context.get_admin_context()

        if 0:self.db=db_api # Stupid hack for code completion in ide

        instance = self.db.instance_get(self.ctx, instance_id)
        assert isinstance(instance, nova.db.sqlalchemy.models.Instance)

        migration_status = self.scheduler_rpc_api.live_migration(ctxt=ctx,
                                                                 block_migration=self.migration_settings.block_migration,
                                                                 disk_over_commit=self.migration_settings.disk_over_commit,
                                                                 instance=instance,
                                                                 dest=hostname)

        LOG.error("Migration status %s" % migration_status)
