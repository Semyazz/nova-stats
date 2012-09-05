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

import nova.openstack.common.rpc.proxy

LOG = logging.getLogger(__name__)

FLAGS = flags.FLAGS

class HealthMonitorAPI(nova.openstack.common.rpc.proxy.RpcProxy):
    pass

    BASE_RPC_API_VERSION = '1.0'
    HEALTH_MONITOR_TOPIC = "health_monitor"

    @staticmethod
    def make_msg(method, **kwargs):
        return {'method': method, 'args': kwargs}

    def __init__(self):
        super(HealthMonitorAPI, self).__init__(
            topic = self.HEALTH_MONITOR_TOPIC,
            default_version=self.BASE_RPC_API_VERSION)


    def raise_alert(self, ctxt, alert):
        self.cast(context=ctxt,
                msg=self.make_msg('raise_alert', alert=alert),
                topic=self.HEALTH_MONITOR_TOPIC,
                version=self.BASE_RPC_API_VERSION)

#        self.fanout_cast(ctxt,
#                         self.make_msg('raise_alert', alert=alert),
#                         None)
#        self.cast(context=ctxt, msg=message, topic="health_monitor",version=None)

