__author__ = 'semy'

import os
from os import path

import datetime

from novastats.rrd.rrd import RrdWrapper
from nova import test

class TestRrdWrapper(test.TestCase):

    def setUp(self):
        super(TestRrdWrapper, self).setUp()


    def test_get_instances(self):

        rrd_root_dir = "/home/semy/lab-os-1/ganglia"

        rrd = RrdWrapper(rrd_root_dir)
        instances = rrd.get_instances_names()

        print instances

    def test_get_instance_stats_names(self):

        rrd_root_dir = "/home/semy/lab-os-1/ganglia"
        rrd = RrdWrapper(rrd_root_dir)

        stats = rrd.get_instance_stats_names('instance-0000002f', 'lab-os-2')

        print stats

    def test_get_hosts_names(self):

        rrd_root_dir = "/home/semy/lab-os-1/ganglia"
        rrd = RrdWrapper(rrd_root_dir)

        stats = rrd.get_hosts_names(clusterName)

        print stats


    def test_get_host_stats_names(self):

        rrd_root_dir = "/home/semy/lab-os-1/ganglia"
        rrd = RrdWrapper(rrd_root_dir)

        stats = rrd.get_host_stats_names('lab-os-2')

        print stats


    def test_join_path(self):
        a = "/home/stack/ganglia"
        b = "Openstack"

        self.assertEqual("/home/stack/ganglia/Openstack", path.join(a, b))

    def test_foreach_dirs(self):
        clusterPath = "/home/semy/lab-os-1/ganglia/Openstack"

#        hostnames = os.listdir(clusterPath)
        hostnames = filter (lambda hostname: hostname != "__SummaryInfo__" ,os.listdir(clusterPath))

#        expected = ["lab-os-2", "lab-os-1", "lab-os-14", "lab-os-15", "__SummaryInfo__"]
        expected = ["lab-os-2", "lab-os-1", "lab-os-14", "lab-os-15"]

        self.assertTrue(len(hostnames) == len(expected), "Count !=")

        for hostname in expected:
            self.assertTrue(hostname in hostnames)

    def test_foreach_files(self):
        clusterPath = "/home/semy/lab-os-1/ganglia/Openstack/lab-os-14"

        instances = filter(lambda file: file.endswith(".rrd") and file.startswith("instance"),os.listdir(clusterPath))

        instances_names = set([TestRrdWrapper.cut_instance_name(instance) for instance in instances])

        print instances_names

    def test_query(self):
        rrd_root_dir = "/home/semy/lab-os-1/ganglia"
        rrd = RrdWrapper(rrd_root_dir)


        endTime = datetime.datetime.now()
        startTime = endTime + datetime.timedelta(seconds=-12000)
        #endTime = startTime + datetime.timedelta(hours=1)

#        instance = "instance-0000002f"
        hostname = "lab-os-2"

        result = rrd.query(startTime, endTime, 'cpu_system', hostname=hostname)

        print result


    def test_query_last_hours(self):
        rrd_root_dir = "/home/semy/lab-os-1/ganglia"
        rrd = RrdWrapper(rrd_root_dir)


        endTime = datetime.datetime.now()
        startTime = endTime + datetime.timedelta(hours=-5)
        #endTime = startTime + datetime.timedelta(hours=1)

        instance = "instance-0000002f"
        hostname = "lab-os-2"

        result = rrd.query(startTime, endTime, 'vcpu_util', instance, hostname)

        print result


    def test_query_start_larger_than_end(self):
        rrd_root_dir = "/home/semy/lab-os-1/ganglia"
        rrd = RrdWrapper(rrd_root_dir)


        endTime = datetime.datetime.now()
        startTime = endTime + datetime.timedelta(hours=-12000)
        #endTime = startTime + datetime.timedelta(hours=1)

        instance = "instance-0000002f"
        hostname = "lab-os-2"

        result = rrd.query(endTime, startTime, 'vcpu_util', instance, hostname)

        print result

    @staticmethod
    def cut_instance_name(name):

        return name.split('.')[0]

#        expected = ["lab-os-2", "lab-os-1", "lab-os-14", "lab-os-15"]

#        self.assertTrue(len(hostnames) == len(expected), "Count !=")

#        for hostname in expected:
#            self.assertTrue(hostname in hostnames)


1346943600000
1346943611000


