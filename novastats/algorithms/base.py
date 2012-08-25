import abc

__author__ = 'semy'


class AlgorithmBase(object):

    __metaclass__ = abc.ABCMeta

    append_method = None

    @abc.abstractmethod
    def execute_algorithm(self, input_data_set):
    #        input_data_set.resources_history
    #        input_data_set.virtual_machines
    #        input_data_set.physical_nodes
        pass
