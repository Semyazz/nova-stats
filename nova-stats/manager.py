# -*- encoding: utf-8 -*-

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

from nova import context
from nova import flags
from nova import manager
from nova.scheduler import rpcapi
from nova.openstack.common import cfg
from nova.openstack.common import importutils
from nova.openstack.common import log as logging
from nova.openstack.common import rpc
from nova.openstack.common import context

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

    class MigrationSettings(object):
        block_migration=None,
        disk_over_commit=None

        def __init__(self):
            self.block_migration = True
            self.disk_over_commit = True

    migration_settings = MigrationSettings()

    def init_host(self):
        LOG.info("Info")
        self.topic = "health.monitor"
        ctx = context.get_admin_context()
        instances = self.db.instance_get_all_by_host(ctx, self.host)

        pass

    def _init_scheduler(self):
        self.scheduler_rpcapi = rpcapi.SchedulerAPI()

    def _init_monitors_connections(self):

        self.conn = rpc.create_connection(new=True)
        LOG.debug(_("Creating Consumer connection for Service %s") % self.topic)

        rpc_dispatcher = self.create_rpc_dispatcher()

        # According to documentation fanout=True => broadcast to all services.
        self.conn.create_consumer(self.topic, rpc_dispatcher, fanout=True)

        # Consume from all consumers in a thread
        self.conn.consume_in_thread()

    def periodic_tasks(self, context, raise_on_error=False):
        pass


    def raise_alert(self, ctxt, message):
        LOG.debug(_("Got message %s") % message)

        #TODO: try get message from node.


    def prepare_resource_allocation_algorithm(self, hostname, resource):
        """
        :param hostname: String
        :param resource: String
        :return:
        """

        collectedData = self.collect_data(hostname, resource)
        virtualMachines = self.get_virtual_machines_locations()
        physicalNodes = self.get_physical_nodes_resources_utilization()

        input_data_set = dict(resources_history=collectedData, virtual_machines=virtualMachines, physical_nodes=physicalNodes)

        migrationPlans = self.create_migration_plans(input_data_set)

        self.execute_plan(migrationPlans)

        pass

    def get_virtual_machines_locations(self):
        pass

    def get_physical_nodes_resources_utilization(self):
        pass

    def create_migration_plans(self, input_data_set):
        #TODO
        pass

    def execute_plan(self, migrationPlans):
        """
        :param migrationPlans: list
        :return:
        """
        try:
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

    def choose_migration_plan(self, plans):
        #TODO
        if len(plans) > 0:
            plan = sorted(plans, key= lambda score : plan.score)
            #plan = plans.reverse().pop()
            return plan
        else:
            raise Exception("There is no migration plan")

    def collect_data(self, hostname, resource):
        """

        :return:
        """
        pass




