# -*- encoding: utf-8 -*-

__docformat__ = 'restructuredtext en'

import rrdtool
import os
from os import path
import datetime
import time

class RrdWrapper:

    cluster_name = ""

    def __init__(self, rrd_rootdir):
        self.rrd_rootdir = rrd_rootdir

    def query(self, startTime, endTime, metricName, instance=None, hostname = "__SummaryInfo__", clusterName = "Openstack"):
        """ Get dictionary with proper data from given period of time and for given node

        :param startTime:
        :type startTime: datetime
        :param endTime:
        :type endTime: datetime
        :param metricName: Metric name.
        :type metricName: String
        :param hostname: Node's hostname.
        :type hostname: String
        :param clusterName: Cluster's name.
        :type clusterName: String
        :return:
        :rtype: Dict
        """

        if metricName is None:
            raise Exception("Null parameter %s", "metricName")

        if endTime is None:
            raise Exception("Null parameter %s", "endTime")

        if startTime is None:
            raise Exception("Null parameter %s", "startTime")

        if startTime > endTime:
            startTime, endTime = endTime, startTime

        start = int(time.mktime(startTime.timetuple()))
        end = int(time.mktime(endTime.timetuple()))

        dirPath = self._get_host_path(hostname, clusterName)

        metricFileName = ""
        if instance is not None:
            metricFileName = ".".join([instance, metricName])
        else:
            metricFileName = metricName
        metricFileName = ".".join([metricFileName, "rrd"])

        filePath = path.join(dirPath, metricFileName)

        if not path.exists(filePath):
            raise Exception("File for stat '%s' not exists: %s" % (metricName, filePath))

        return self._fetch_data(filePath, start, end)


    def _fetch_data(self, rrdObject, startTime, endTime):
        """ Fetch data from RRD archive for given period of time.

        :param rrdObject: RRD
        :type rrdObject: String
        :type startTime: int
        :type endTime: int
        :return: Dictionary with data from RRD archive.
        :rtype: Dict
        """

        print rrdObject

        if not path.exists(rrdObject):
            raise Exception("File not exists: %s" % rrdObject)

        print "%s - %s" % (startTime, endTime)

        return rrdtool.fetch(rrdObject, "AVERAGE", "--start", str(startTime), "--end", str(endTime))

    def get_instances_names(self, clusterName = "Openstack"):

        clusterPath = path.join(self.rrd_rootdir, clusterName)
        hostsNames = filter (lambda hostname: hostname != "__SummaryInfo__" ,os.listdir(clusterPath))

        result = dict()

        for hostname in hostsNames:
            result[hostname] = self._get_instances_names(path.join(clusterPath, hostname))

        return result


    def get_instance_stats_names(self, instanceName, hostname, clusterName = "Openstack"):
        hostPath = self._get_host_path(hostname, clusterName)

        instance_stats = filter (lambda filename: filename.startswith(instanceName), os.listdir(hostPath))

        instance_stats_names = [x.split('.')[1] for x in instance_stats]
        return instance_stats_names


    def get_hosts_names(self, clusterName = "Openstack"):

        clusterPath = path.join(self.rrd_rootdir, clusterName)
        hostsNames = filter (lambda hostname: hostname != "__SummaryInfo__" ,os.listdir(clusterPath))

        return hostsNames


    def get_host_stats_names(self, hostname, clusterName = "Openstack"):

        hostPath = self._get_host_path(hostname, clusterName)
        host_stats = filter (lambda filename: not filename.startswith("instance"), os.listdir(hostPath))

        host_stats_names = [x.split('.')[0] for x in host_stats]
        return host_stats_names


    def _get_host_path(self, hostname, clusterName):
        return path.join(self.rrd_rootdir, clusterName, hostname)


    def _get_instances_names(self, root_path):
        instances = filter(lambda file: file.endswith(".rrd") and file.startswith("instance"),os.listdir(root_path))
        return set([instance.split('.')[0] for instance in instances])

    def get_info(self, rrdObject, clusterName = "Openstack"):
        #TODO: translate into human-redable output.
        return rrdtool.info(rrdObject)