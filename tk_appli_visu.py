import matplotlib.pyplot as plt
import numpy as np
import time
from scipy import signal

from lib_connector import DataConnector
from lib_netitem import NetworkItem, SrvManagement
from lib_log import Log



class MaVisu(NetworkItem, SrvManagement)	:
	def __init__(self, name, hote, port, data_to_draw):
		NetworkItem.__init__(self, name, hote, port)
		self.set_connection(False, 'data', DataConnector, data_to_draw)
		self.filter = True
		self.record_action('visu_filter_toggle', 'short', self.action_filter)
		self.init_visu()
		self.fenetre_visu = [-1, 0]
		self.intervalle = 4
		self.derive_min = None
		self.derive_max = None
		self.derive_last = None
		self.affiche_last = np.round(time.perf_counter(),3)
		self.color = {}
		self.start = time.time()
		Log.filter(2)
		self.gestdata = {}
		self.reconnect()
	
	def init_visu(self):
		#self.title("VISU DATA")
		self.figure = plt.figure()
		self.ax = plt.subplot(111)
		plt.get_current_fig_manager().window.title("VISU DATA")
		
	def maj_visu(self, tps):
		if tps > self.fenetre_visu[1]:
			deb = tps//self.intervalle*self.intervalle
			self.fenetre_visu = [deb, deb+self.intervalle]
		
			plt.cla()
			self.ax.set_xlim(self.fenetre_visu)
			#self.ax.set_ylim([-25,25])
			self.ax.set_ylim([-4000,4000])
			pass
			tps_change = np.round(time.perf_counter(),3)
			Log.send("{} {} {}".format(self.fenetre_visu, tps_change-self.affiche_last, time.time()-(self.fenetre_visu[0]+self.start)), level=2)
			self.affiche_last = tps_change
			
	def action_filter(self, *args, filter=None, **kargs):
		if filter is None:
			filter = not self.filter
		self.filter = filter
		Log.send("set filter:{}".format(filter), level=2)
		
		
	def show_data(self, name, x, y, color='r'):
		t = x - self.start
		
		self.ax.plot(t, y, color=color)
		
	def answer_std(self, *args, **kargs):
		print("answer",args, kargs)
				
	def process_in_data(self):
		if 'connect_data' not in self.__dict__ or self.connect_data is None:
			print("not yet", list(self.__dict__))
			print("not yet2", list(self.exposed_actions))
			print("==")
			return
		d = self.connect_data.next_received()
		self.maj_visu(time.time()-self.start)

		while d is not None:
			now = time.perf_counter()
			
			if d.name not in self.gestdata:
				b, a = signal.butter(4, 50/1000, 'low', analog=False)
				self.gestdata[d.name] = {'color':['b','r','y','k'][len(self.gestdata)], 
										'freq':1000, 
										'lastval':None,
										'butter':{'a':a, 'b':b},
										'cache':{'x':np.array([]), 'y':np.array([])}}
			
			nbval = len(d.val)
			t = np.linspace(d.time, d.time+nbval/self.gestdata[d.name]['freq'], nbval)
			
			if not self.filter:
				if self.gestdata[d.name]['lastval'] is not None:
					link_t = np.array([self.gestdata[d.name]['lastval'][0], t[0]])
					link_v = np.array([self.gestdata[d.name]['lastval'][1], d.val[0]])
					self.show_data(d.name, link_t, link_v, self.gestdata[d.name]['color'])
				self.show_data(d.name, t, d.val, self.gestdata[d.name]['color'])			
				self.gestdata[d.name]['cache']={'x':np.array([]), 'y':np.array([])}
				self.gestdata[d.name]['lastval'] = [t[-1], d.val[-1]]
			else:			
				x = np.concatenate([self.gestdata[d.name]['cache']['x'], t])
				y = np.concatenate([self.gestdata[d.name]['cache']['y'], d.val])
				
				res = signal.filtfilt(**self.gestdata[d.name]['butter'], x=y).tolist()
				self.show_data(d.name, x, res, self.gestdata[d.name]['color'])			

				if x[nbval-1] < self.fenetre_visu[0] + self.start:
					#on abandonne les 1eres valeurs
					x = x[nbval:]
					y = y[nbval:]
				
				self.gestdata[d.name]['cache']={'x':x, 'y':y}
				self.gestdata[d.name]['lastval'] = [t[-1], d.val[-1]]

			self.derive_last = now - t[-1]
			if self.derive_min is None or self.derive_min > self.derive_last:
				self.derive_min = self.derive_last
			if self.derive_max is None or self.derive_max < self.derive_last:
				self.derive_max = self.derive_last
			d = self.connect_data.next_received()
				

				
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
	
	name = "mavisu"
	if len(args) > 0:
		name = args[0]
	
	appli = MaVisu(name, HOST, PORT, "*")

	keypress = kb_func()
	cpt =0
	plt.pause(0.01)
	while keypress != 'q' and plt.get_current_fig_manager().window.state()!='withdrawn' and appli.running:
		## les commandes claviers
		if keypress and keypress == 'a':
			print(appli.connect_central.isconnected())
		elif keypress and keypress == 'z':
			print("Reconnexion au central")
			appli.reconnect()
		elif keypress and keypress == 'e':
			appli.action_filter(filter=not appli.filter)
		elif keypress and keypress == 'r':
			appli.waitfor(appli.ask_action('collect-data', 'srv_info_data'), callback=appli.answer_infodatasocket)
			
		keypress = kb_func()	

		#les echanges socket
		appli.do_service_process()
		#time.sleep(0.01)		
		appli.process_in_data()
		#print(plt.get_current_fig_manager().window.__dict__)
		plt.pause(0.01)
		
		'''
		cpt+=1
		if cpt%40==0:
			plt.pause(0.01)
			pass
		else:
			time.sleep(0.01)
		'''
	print("DERIVE", appli.derive_min, appli.derive_max, appli.derive_last)