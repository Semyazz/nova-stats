__author__ = 'student'
import datetime


class Boundaries(object):

    CPU_UPPER_BOUND = 0.80
    CPU_LOWER_BOUND = 0.4

    NETWORK_UPPER_BOUND = 0.80
    NETWORK_LOWER_BOUND = 0.4

    MEMORY_UPPER_BOUND = 0.80
    MEMORY_LOWER_BOUND = 0.4


class MigrationParams(object):

    STABILIZATION_TIME_DELTA = datetime.timedelta(minutes=5)
