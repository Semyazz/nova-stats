import abc

__author__ = 'semy'


class AlgorithmBase(object):

    __metaclass__ = abc.ABCMeta

    append_method = None

    @abc.abstractmethod
    def execute_algorithm(self, input_data_set):
        pass

    @abc.abstractmethod
    def create_migration_plans(self, input_data_set):
        pass