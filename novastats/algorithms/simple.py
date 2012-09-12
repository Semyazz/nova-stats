__author__ = 'semy'

from base import AlgorithmBase

class SimpleBackpackAlgorithm(AlgorithmBase):

    def execute_algorithm(self, input_data_set):
        """
            Bin packing Algorithm
        """



        pass

    def create_migration_plans(self, input_data_set):

        plans = list()

        def append_recipe(vm_hostname, hostname_from, hostname_to):
            plans.append(dict(vm = vm_hostname, host_from = hostname_from, host_to = hostname_to))

        self.append_method = append_recipe

        self.execute_algorithm(input_data_set)

        return plans
