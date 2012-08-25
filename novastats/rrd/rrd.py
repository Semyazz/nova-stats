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

    def query(self, startTime, endTime, metricName, hostname = "__SummaryInfo__", clusterName = ""):
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
            tmp = startTime
            startTime = endTime
            endTime = tmp
        elif endTime > startTime:
            tmp = endTime
            endTime = startTime
            startTime = tmp

        start = int(time.mktime(startTime.timetuple()) * 1000)
        end = int(time.mktime(endTime.timetuple()) * 1000)

        filePath = ""

        if clusterName is None:
            filePath = path.join(self.rrd_rootdir, hostname, metricName + ".rrd")
        else:
            filePath = path.join(self.rrd_rootdir, clusterName, hostname, metricName + ".rrd")


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

        if not path.exists(rrdObject):
            raise Exception("File not exists %s" % rrdObject)

        return rrdtool.fetch(rrdObject, "AVERAGE", "--start", startTime, "--end", endTime)

    def get_info(self, rrdObject):
        #TODO: translate into human-redable output.
        return rrdtool.info(rrdObject)