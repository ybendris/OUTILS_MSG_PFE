import sys
import getopt
import msvcrt

import time
import math

import random

import numpy as np
from collections import deque

from lib_netitem import NetworkItem, SrvManagement
from lib_connector import DataConnector

from lib_msg import MsgData

"""
	Stub pour voir comment pourrait fonctionner un superviseur
"""
class Stub(NetworkItem, SrvManagement):	
	def __init__(self,  name, hote, port, params=[]):
		NetworkItem.__init__(self, name, hote, port)		
		self.set_connection(True, 'data', DataConnector, params)
		self.go()
		self.reconnect()
		
	def go(self):
		self.data_params = ['{}.sin'.format(self.name)]
		self.data = {'{}.sin'.format(self.name):deque()}

		self.delta = time.time() - time.perf_counter()
		self.gen_param()
		self.d1 = random.random()*2*np.pi
		self.d2 = random.random()*2*np.pi
		self.d3 = random.random()*2*np.pi
		self.pause_until = 0
		
		
		self.record_action('dem_accelerate', 'short', self.action_accelerate)
		self.record_action('dem_accelerate-to', 'short', self.action_accelerate_to)
		self.record_action('dem_decelerate', 'short', self.action_decelerate)
		self.record_action('dem_pause', 'long', self.action_pause_1)
		self.record_action('dem_change', 'short', self.action_regen_param)


	def gen_param(self):
		self.fq=random.randint(1,6)/4
		self.a0=random.randint(0,20)/10
		self.a1=random.randint(5,10)
		self.a2=random.randint(0,20)/random.randint(3,8)
		self.a3=random.randint(0,20)/random.randint(3,5)
		
	def action_regen_param(self, *karg):
		print(karg)
		fq=random.randint(1,6)/4
		a0=random.randint(0,20)/10*10
		a1=random.randint(5,10)
		a2=random.randint(0,20)/random.randint(3,8)
		a3=random.randint(0,20)/random.randint(3,5)
		
		ytransit = None
		if 'last' in self.__dict__ and self.last is not None:
			#il faut calculer le decalage phi
			x = self.last
			ytransit = self.a0+self.a1*np.sin(2*np.pi*self.fq*x+self.d1)+self.a2*np.sin(2*2*np.pi*self.fq*x+self.d2)+self.a3*np.sin(3*2*np.pi*self.fq*x+self.d3)
			
		self.gen_param()
		if ytransit is not None:
			delay = self.next_y(ytransit)
			self.yfix = ytransit
			self.pause_until = self.last+delay
			#self.action_pause(delay)
			
	
	def next_y(self, y_target):
		x = np.linspace(self.last, self.last+2, 2000)
		y = self.a0+self.a1*np.sin(2*np.pi*self.fq*x+self.d1)+self.a2*np.sin(2*2*np.pi*self.fq*x+self.d2)+self.a3*np.sin(3*2*np.pi*self.fq*x+self.d3)
		calc = np.around(np.absolute(y-y_target),1)
		m = np.amin(calc)
		indexs = np.where(calc == m)
		i = indexs[0][0]
		
		return i/1000		

	def action_accelerate(self, *karg):
		self.action_accelerate_to(1.2)

	def action_decelerate(self, *karg):
		self.action_accelerate_to(0.6)

	def action_accelerate_to(self, val, *karg):
		x = self.last
		self.d1 -= 2*np.pi*x*self.fq*(val-1)
		self.d2 -= 2*2*np.pi*x*self.fq*(val-1)
		self.d3 -= 3*2*np.pi*x*self.fq*(val-1)
		self.fq *= val

	def action_pause_1(self, *param):
		self.action_pause(1, *param)
		
	def action_pause(self, delay, *param):
		x = self.last
		if self.pause_until < self.last:
			self.pause_until = self.last+delay
			'''
			if y_target is not None:
				self.yfix = y_target
			else:
				self.yfix = self.a0+self.a1*np.sin(2*np.pi*self.fq*x+self.d1)+self.a2*np.sin(2*2*np.pi*self.fq*x+self.d2)+self.a3*np.sin(3*2*np.pi*self.fq*x+self.d3)
			'''
			self.yfix = self.a0+self.a1*np.sin(2*np.pi*self.fq*x+self.d1)+self.a2*np.sin(2*2*np.pi*self.fq*x+self.d2)+self.a3*np.sin(3*2*np.pi*self.fq*x+self.d3)
		else:
			#on ne change pas yfix
			self.pause_until +=delay
		
		#on recalcule le decalage phi
		self.d1 -= 2*np.pi*self.fq*delay
		self.d2 -= 2*2*np.pi*self.fq*delay
		self.d3 -= 3*2*np.pi*self.fq*delay


	def remplit(self):
		if 'last' not in self.__dict__ or self.last is None:
			self.first = round(time.perf_counter(),3)
			self.last = self.first
		elif self.last < self.pause_until:
			now = time.perf_counter()
			if now > self.pause_until:
				now = self.pause_until
			val0 = int((self.last-self.first)*1000)
			nbval = int((now-self.last)*1000)
			x = np.linspace(self.last, now, nbval)
			y = np.full(nbval, self.yfix)
			self.data['{}.sin'.format(self.name)].append({'date':self.last+self.delta, 'counter':val0, 'data':y.tolist()})
			self.last = now
		else:
			now = time.perf_counter()			
			val0 = int((self.last-self.first)*1000)
			
			nbval = int((now-self.last)*1000)
			x = np.linspace(self.last, now, nbval)
			y = self.a0+self.a1*np.sin(2*np.pi*self.fq*x+self.d1)+self.a2*np.sin(2*2*np.pi*self.fq*x+self.d2)+self.a3*np.sin(3*2*np.pi*self.fq*x+self.d3)
			y = y*100
			self.data['{}.sin'.format(self.name)].append({'date':self.last+self.delta, 'counter':val0, 'data':y.tolist()})
			self.last = now

	def do_service_process(self):
		super().do_service_process()
		
		while self.data['{}.sin'.format(self.name)]:
			d = self.data['{}.sin'.format(self.name)].popleft()	
			if 'connect_data' in self.__dict__ and self.connect_data and self.connect_data.isconnected():
				self.connect_data.send(MsgData(name='{}.sin'.format(self.name), time=d['date'], counter=d['counter'], val=d['data']))



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
	test = Stub(name, HOST, PORT)

	keypress = kb_func()		
	check_data = time.perf_counter()
	while keypress != 'q' and test.running:
		## les commandes claviers
		if keypress and keypress == 'a':
			print(test.connect_central.isconnected())
		elif keypress and keypress == 'z':
			test.reconnect()
		elif keypress and keypress == 'e':
			#on change les variables
			test.action_regen_param()			
		elif keypress and keypress == 'r':
			test.action_accelerate()
		elif keypress and keypress == 't':
			test.action_decelerate()
		elif keypress and keypress == 'y':
			test.action_pause(1)
			
			
		keypress = kb_func()	

		#les echanges socket
		test.do_service_process()

		
		if time.perf_counter() > check_data+0.015:
			test.remplit()
			check_data = time.perf_counter()
			
		time.sleep(0.01)


