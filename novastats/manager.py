# -*- encoding: utf-8 -*-
from collections import namedtuple

__docformat__ = 'restructuredtext en'

import errno
import inspect
import os
import random
import signal
import sys
import time
import datetime

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

from ceilometer.ganglia.rpcapi import HealthMonitorNodeAPI
from algorithms.simple import SimpleBackpackAlgorithm
from rrd.rrd import RrdWrapper
from novastats.structures.host import Host

from rpcapi import HealthMonitorAPI

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

    RRD_ROOT_DIR = ""

#    def __init__(self, topic=None):
#        print "HelloMgr"
##        self.topic = topic

    # RPC API Implementation -------------------------------------------------------------------------------------------
    def raise_alert(self, ctx=None, alert=None):
        LOG.info(alert)

        if not self.local_storage:
            self.local_storage = RrdWrapper(self.RRD_ROOT_DIR)

        endTime = datetime.datetime.now()
        startTime = endTime - datetime.timedelta(hours=1)

        hostNames = self.local_storage.get_hosts_names()
        instanceNames = self.local_storage.get_instances_names()

        hosts = []

        for hostName in hostNames:
            LOG.info("collection info from host %s", hostName)
            hosts.append(Host(self.local_storage,instanceNames, hostName, startTime, endTime))

#        print alert
    #-------------------------------------------------------------------------------------------------------------------


    # Manager inherited ------------------------------------------------------------------------------------------------
    def init_host(self):
        self.topic = HealthMonitorAPI.HEALTH_MONITOR_TOPIC
        self.ctx = context.get_admin_context()
        self.ctx.read_deleted = "no"
        self.instances = self.db.instance_get_all_by_host(self.ctx, self.host)
        self.migration_algorithm = SimpleBackpackAlgorithm()

        self._init_monitors_connections()
#        self._init_scheduler()

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
        self.scheduler_rpc_api = nova.scheduler.rpcapi.SchedulerAPI()

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



    def prepare_resource_allocation_algorithm_input(self, hostname, vm_name, resource):
        """
            Hostname is virtual machine's hostname (name)
        :param hostname: String
        :param resource: String
        :return:
        """

        virtualMachines = self.get_virtual_machines_locations()
        collectedData = self.collect_data(hostname, vm_name, resource)
        physicalNodes = self.get_physical_nodes_resources_utilization()

        input_data_set = dict(resources_history=collectedData, virtual_machines=virtualMachines, physical_nodes=physicalNodes)

        migrationPlans = self.migration_algorithm.create_migration_plans(input_data_set)

        self.execute_plan(migrationPlans)

        pass

    def create_migration_plans(self, input_data_set):
        #TODO
        pass

    def choose_migration_plan(self, plans):
        #TODO
        if len(plans) > 0:
            plans = sorted(plans, key= lambda score : plan.score)
            plan = plans.reverse().pop()
            return plan
        else:
            raise Exception("There is no migration plan")

    def execute_plan(self, migrationPlans):
        """
        Executes migration plan. Migrate VMs to given nodes.
        :param migrationPlans: list
        :return:
        """
        try:
            self._init_scheduler()
            plan = self.choose_migration_plan(migrationPlans)
            ctx = context.get_admin_context()

            for instance in plan.instances:
                migration_status = self.scheduler_rpc_api.live_migration(ctxt=ctx,
                        block_migration=self.migration_settings.block_migration,
                        disk_over_commit=self.migration_settings.disk_over_commit,
                        instance_id=instance.id,
                        dest=instance.dest,
                        topic = FLAGS.compute_topic)

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




