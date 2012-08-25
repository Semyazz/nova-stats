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

import eventlet
import greenlet
eventlet.monkey_patch()

import nova.scheduler
from nova import context
from nova import flags
from nova import manager
from nova.scheduler import rpcapi
from nova.openstack.common import cfg
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova.openstack.common import rpc
from nova.openstack.common import context

from ceilometer.healthmonitor.rpcapi import HealthMonitorNodeAPI
from algorithms.simple import SimpleBackpackAlgorithm


from rpcapi import HealthMonitorAPI

try:
    import nova.openstack.common.rpc as nova_rpc
except ImportError:
    # For Essex
    import nova.rpc as nova_rpc

LOG = logging.getLogger(__name__)
print __name__
FLAGS = flags.FLAGS

class HealthMonitorManager(manager.Manager):
    BASE_RPC_API_VERSION = '1.0'

#    def __init__(self, topic=None):
#        print "HelloMgr"
##        self.topic = topic

    # RPC API Implementation -------------------------------------------------------------------------------------------
    def raise_alert(self, ctx=None, alert="1"):
        print alert

        #TODO: try get message from node.
    #-------------------------------------------------------------------------------------------------------------------


    # Manager inherited ------------------------------------------------------------------------------------------------
    def init_host(self):
        LOG.info("Info testasdfasdfadsfa")
        self.topic = "health_monitor"
        LOG.info("Context")
        self.ctx = context.get_admin_context()
        self.ctx.read_deleted = "no"
        LOG.info("Got context")
        instances = self.db.instance_get_all_by_host(self.ctx, self.host)
        LOG.info("Got instances")
        self.migration_algorithm = SimpleBackpackAlgorithm()

        self._init_monitors_connections()
        LOG.info("initialized consumer")
        pass

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

        LOG.info(self.conn.conf.__dict__)

        LOG.info( "%s" % self.conn)
        LOG.debug(self.conn)
        LOG.debug(_("Creating Consumer connection for Service %s") % self.topic)

        rpc_dispatcher = self.create_rpc_dispatcher()

        # According to documentation fanout=True => broadcast to all services.
        self.conn.create_consumer(self.topic, rpc_dispatcher, fanout=True)

        # Consume from all consumers in a thread
        self.conn.consume_in_thread()

        time.sleep(10)

        api = HealthMonitorAPI()
        #LOG.info(api.topic)
        api.raise_alert(self.ctx, alert= {"alert":"test"})

#    test_thread_obj = None
#
#    def show_log(self):
#        self.x = 100
#        LOG.info("helo")
#
#    def test_thread(self):
#
#        """Consumer from all queues/consumers in a greenthread"""
#        def _test_thread():
#            try:
#                self.show_log()
#            except greenlet.GreenletExit:
#                LOG.error("OPS")
#        if self.test_thread_obj is None:
#            self.test_thread_obj = eventlet.spawn(_test_thread)
#        return self.test_thread_obj


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
                migration_status = self.scheduler_rpcapi.live_migration(ctxt=ctx,
                        block_migration=self.migration_settings.block_migration,
                        disk_over_commit=self.migration_settings.disk_over_commit,
                        instance_id=instance.id,
                        dest=instance.dest,
                        topic = FLAGS.compute_topic)

        except:
            raise

    def collect_data(self, hostname, vm_name, resource):
        """
            Collect historical data about resource utilization for given node (hostname/virtual machine)
        :return:
        """

        #node_topic = '%s.%s' % (HealthMonitorNodeAPI.HEALTH_MONITOR_NODE_TOPIC, hostname)
        health_rpc_api = HealthMonitorNodeAPI(hostname)

        if health_rpc_api is None:
            raise Exception("Unable to get health_monitor_node RPC API object")

        message = {"resource" : resource, "vm_name": vm_name}

        ctx = context.get_admin_context()
        return health_rpc_api.collect_recent_stats(ctx, message)

    def get_virtual_machines_locations(self):
        """
        Gets dictionary {"physical node hostname": set of virtual machines (their hostnames)}
        :return:
        """
        pass

    def get_physical_nodes_resources_utilization(self):
        pass



