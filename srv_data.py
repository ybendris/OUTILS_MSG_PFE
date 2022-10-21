import numpy as np
import pandas as pd
import time
from scipy import signal
from collections import deque

from lib_connector import DataConnector, LogConnector
from lib_netitem import NetworkItem, SrvManagement
from lib_log import Log


class DataCollect(NetworkItem, SrvManagement):
	def __init__(self, name, hote, port):
		NetworkItem.__init__(self, name, hote, port)
		self.set_connection(False, 'data', DataConnector)
		self.start = time.time()
		self.data = {}
		self.time_digest = self.start
		self.reconnect()

	def process_in_data(self):
		class DataCollect:
			def __init__(self, name, freq):
				self.name = name
				self.period_ms = int(1000/freq)
				self.to_treat = []
				self.long_term = pd.DataFrame({'t':[], 'val':[]})
				self.to_store = pd.DataFrame({'t':[], 'val':[]})
				self.counter = 0
				self.current = None
				self.begin_current = None
				self.end_current = None
				
			def append(self, begin, val):
				begin_new = int(begin*1000) #exprimé en ms
				if self.end_current is None or self.end_current<begin_new:
					if self.end_current is not None:
						#=>self.end_current<begin_current => un saut dans le temps
						self.to_treat.append({'begin':self.begin_current, 'queue':self.current})
					self.current = deque()
					self.begin_current = begin_new
					pass
				self.end_current = begin_new+len(val)*self.period_ms
				self.current.append(val)
				
			def digest(self):
				#on vide 'current' si il est en cours
				if self.end_current is not None:
					self.to_treat.append({'begin':self.begin_current, 'queue':self.current})
					self.current = None
					self.begin_current = None
					self.end_current = None
					
				#on s'occupe de to_treat
				reliquat = []
				go_on = True
				for set in self.to_treat:
					current_end = set['begin']
					y = np.array([])
					#on depile toutes les array qui se suivent
					while set['queue']:
						v = set['queue'].popleft()
						current_end += len(v)*self.period_ms							
						y = np.concatenate((y,v))
												
					nb_val = len(y)
					if nb_val>0:
						end = set['begin']+nb_val*self.period_ms
						x = np.linspace(set['begin'], end, nb_val)
						self.to_store = self.to_store.append(pd.DataFrame({'t':x, 'val':y}), ignore_index=True)
						#on a x et y
						#et maintenant ? 
						#on calcule les elements long-terme
						#a 20Hz ça suffit => 50ms
						b, a = signal.butter(4, 50/1000, 'low', analog=False)
						y2 = signal.filtfilt(b, a, y)
						self.long_term = self.long_term.append(pd.DataFrame({'t':x[::10], 'val':y2[::10]}))
						
				self.to_treat = []
		
		tps = time.time()
		#pour la lecture des données
		if 'connect_data' in self.__dict__ and self.connect_data is not None:
			howmany = 0
			#on parcourt toutes les données recues
			d = self.connect_data.next_received()
			while d is not None:			
				howmany += 1
				#on les stocke
				try:					
					self.data[d.name].append(d.time, d.val)
				except:
					"""
					if d.name not in self.data_params:
						self.data_params.append(d.name)
					"""
					if d.name not in self.data:
						self.data[d.name] = DataCollect(d.name, 1000)
						self.data[d.name].append(d.time, d.val)
						Log.send("creation {}".format(d.name))
					else:
						Log.send("stop on error", direction="error")
						#on relance pour voir apparaitre l'erreur
						self.data[d.name].append(d.time, d.val)
						pass
							
				self.data[d.name].counter +=1
				if self.data[d.name].counter%100==0:
					Log.send('decal:{} sur {} [{}elem] [{}]'.format(d.time-tps, d.name, howmany, tps), level=3, direction="suivi")
					
				d = self.connect_data.next_received()
					

			if howmany>3:
				Log.send("lecture groupée de {} donnée".format(howmany), level=2, direction="trace")
					
	
		#pour le traitement des données deja presentes
		##faire une boucle sur le temps long pour les données obsolette
		if tps-self.time_digest >= 2:
			#on verifie qu'il n'y a pas de nouveaux producteurs de données
			#self.update_client()
			for d in self.data:
				self.data[d].digest()
			
			Log.send("processing time : {}s after {}s".format(time.time()-tps, tps-self.time_digest), level=2, direction="trace")
			
			self.time_digest = tps		
	
	def todisk(self, dir):
		for d in self.data:
			print("========")
			self.data[d].digest()
			print(d)
			print(self.data[d].to_store)
		
				
if __name__ == '__main__':
	import sys
	import getopt
	import msvcrt
	
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
	
	name = "collect-data"
	if len(args) > 0:
		name = args[0]	
	
	appli = DataCollect(name, HOST, PORT)

	keypress = kb_func()
	cpt =0
	while keypress != 'q' and appli.running:
		## les commandes claviers
		if keypress and keypress == 'a':
			print(appli.connect_central.isconnected())
		elif keypress and keypress == 'z':
			print("Reconnexion au central")
			appli.reconnect()
		elif keypress and keypress == 'e':
			print("Démarrage du server data")
			appli.waitfor(appli.ask_action('central', 'bus_newpeer'), callback=appli.answer_startdatapoolsocket)
			pass
		elif keypress and keypress == 'r':
			print("Connection de tous")
			#appli.waitfor(appli.ask_action('central', 'bus_list'), callback=appli.answer_connect_data_all)
			appli.update_client()
		elif keypress and keypress == 't':
			print(appli.connect_collect.sok)
		
		time.sleep(0.01)
		keypress = kb_func()	

		#les echanges socket
		appli.do_service_process()
		#time.sleep(0.01)		
		appli.process_in_data()
		

	appli.todisk(".")