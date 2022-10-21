import sys
import getopt
import msvcrt

import time

#import csv
import pandas as pd
import numpy as np
from collections import deque
from scipy import signal

from lib_netitem import NetworkItem, SrvManagement
from lib_connector import DataConnector

from lib_msg import MsgData


"""
	Stub pour voir comment pourrait fonctionner un superviseur
"""
class StubFile(NetworkItem, SrvManagement):
	def __init__(self,  name, filename, hote, port):
		NetworkItem.__init__(self, name, hote, port)
		with open(filename,'r') as fp:
			line = fp.readline()
			lparams = line.rstrip().split("\t")
			line = fp.readline()
			lunits = line.rstrip().split("\t")
			line = fp.readline()
			start = float(line.rstrip().split("\t")[0])
			
		self.last = 0
		
		params = []
		self.data = {}
		for p in lparams[1:]:
			params.append("{}.{}".format(name, p))
			self.data["{}.{}".format(name, p)]=deque()
		print(params)
		self.set_connection(True, 'data', DataConnector, params)

		self.df = pd.read_csv(filename, header=None, skiprows=2, delimiter='\t', decimal=".", names=lparams)
		self.start = start
		self.action_raz_courbe()
		self.reconnect()		
		self.record_action('stb_raz_courbe', 'short', self.action_raz_courbe)

		
	def action_raz_courbe(self, *args, **kargs):
		self.tref = self.start-time.perf_counter()
		self.last = self.tref
		self.delta = time.time() -self.start		

		
	def remplit(self):
		tnow = time.perf_counter()+self.tref
		
		ssdf = self.df[(self.df['t']>self.last)&(self.df['t']<=tnow)]
		if len(ssdf)>15:
			t = ssdf['t']
			for dname in self.data_params:
				d = dname[len(self.name)+1:]
				val = ssdf[d].tolist()
				#res = signal.filtfilt(self.b, self.a, val).tolist()
								
				self.data[dname].append({'date':t.iloc[0]+self.delta, 'counter':0, 'data':val})
			self.last = tnow
		

	def do_service_process(self):
		super().do_service_process()

		for dname in self.data_params:
			while self.data[dname]:
				d = self.data[dname].popleft()	
				if 'connect_data' in self.__dict__ and self.connect_data and self.connect_data.isconnected():
					self.connect_data.send(MsgData(name=dname, time=d['date'], counter=d['counter'], val=d['data']))


if __name__ == '__main__':
	def kb_func():
		if msvcrt.kbhit():
			try:
				ret = msvcrt.getch().decode()
				return ret
			except:
				pass

	HOST = '127.0.0.1'	# The server's hostname or IP address
	PORT = 65432		# The port used by the server

	opts, args = getopt.getopt(sys.argv[1:], "")
	
	name = args[0]
	filename = args[1]
	test = StubFile(name, filename, HOST, PORT)

	keypress = kb_func()		
	check_data = time.perf_counter()
	while keypress != 'q' and test.running:			
		## les commandes claviers
		if keypress and keypress == 'a':
			print(test.connect_central.isconnected())
		elif keypress and keypress == 'z':
			test.reconnect()
		elif keypress and keypress == 'r':
			test.action_raz_courbe()
			
		keypress = kb_func()	

		#les echanges socket
		test.do_service_process()
		
		if time.perf_counter() > check_data+0.015:
			test.remplit()
			check_data = time.perf_counter()
			
		time.sleep(0.01)
