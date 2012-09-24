import threading
import datetime
import time
import math
import sys

class CpuBusyThread(threading.Thread):
	def run(self):
		super(CpuBusyThread, self).__init__()
		self._stop = threading.Event()
		self.runCpuIntensive()		

	def stop(self):
		self._stop.set()

	def stopped(self):
		return self._stop.isSet()

	def runCpuIntensive(self):
            while True:
                for i in xrange(2181818):
                    if self.stopped(): return
		    x = 0.000001
		    y = math.sin(x)
		    y = y + 0.00001

print sys.argv

timeInterval = float(sys.argv[1])
timeWithoutWorkload = float(sys.argv[2])

while True:
    t = CpuBusyThread()
    t.start()
    time.sleep(timeInterval)
    t.stop()
    time.sleep(timeWithoutWorkload)
