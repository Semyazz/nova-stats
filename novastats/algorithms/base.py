import abc

__author__ = 'semy'

from novastats.structures.host import Host
from novastats.structures.vm import Vm

class MigrationItem(object):

    def __init__(self, virtualMachine, host):
        assert isinstance(virtualMachine, Vm)
        assert isinstance(host, Host)

        self._instance = virtualMachine
        self._host = host

    @property
    def instance_id(self):
        return self._instance.InstanceName

    @property
    def hostname(self):
        return self._host.Hostname



class AlgorithmBase(object):

    __metaclass__ = abc.ABCMeta

    append_method = None

    @abc.abstractmethod
    def execute_algorithm(self, input_data_set):
        pass

    @abc.abstractmethod
    def create_migration_plans(self, input_data_set):
        pass

    @abc.abstractmethod
    def get_migration_plans(self):
        pass
