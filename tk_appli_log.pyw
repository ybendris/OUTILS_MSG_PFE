import tkinter as tk
from tkinter import ttk

from lib_connector import LogConnector
from lib_netitem import NetworkItem, SrvManagement

from collections import deque
from lib_log import Log

import time

class app(tk.Tk, NetworkItem, SrvManagement):
	def __init__(self, hote, port):
		tk.Tk.__init__(self)
		NetworkItem.__init__(self, "VisuLog", hote, port)
		#consommateur de Log
		self.set_connection(False, 'log', LogConnector)
		self.l_compo = ['hip', 'hop']
		self.cpn_selected = 'all'
		self.index_resize = 0
		self.level = 2
		self.levels = [1, 2, 3]
		self.init_gui()
		self.liste_log = []
		self.time_log = None
		#on limite la production de log ici sinon 1 action engendrent plusieurs actions qui engendre...
		Log.filter(2)
		self.reconnect()

	def init_gui(self):
		self.title("VISU LOG")
		self.protocol('WM_DELETE_WINDOW', self.close_window)
		#self.bind('<Configure>', self.resize)

		columns = ['time', 'component', 'level', 'direc', 'message']

		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		frame = tk.Frame(self)
		frame.grid(row=0, column=0, sticky='new')
		self.combo_cpn = ttk.Combobox(frame, values=self.l_compo, state="readonly")
		self.combo_cpn.pack(side=tk.LEFT)
		self.combo_cpn.bind("<<ComboboxSelected>>", self.select_component)

		self.combo_lvl = ttk.Combobox(frame, values=self.levels, state="readonly")
		self.combo_lvl.pack(side=tk.LEFT)
		self.combo_lvl.bind("<<ComboboxSelected>>", self.select_level)

		self.tree = ttk.Treeview(self, columns=columns, show='headings')
		self.tree.grid(row=1, column=0, sticky='nsew')
		self.tree.grid_columnconfigure(0, weight=1)
		self.tree.grid_rowconfigure(1, weight=1)
		
		scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
		self.tree.configure(yscroll=scrollbar.set)
		scrollbar.grid(row=1, column=1, sticky='ns')

		for i in columns:
			self.tree.column(i, anchor="w")
			self.tree.heading(i, text=i, anchor="w")

		#for index, row in df.iterrows():
		#	self.tree.insert("", "end", text=index, values=list(row))


		self.tree.column('time', width=150, stretch=tk.NO)
		self.tree.column('component', width=120, stretch=tk.NO)
		self.tree.column('level', width=40, stretch=tk.NO)
		self.tree.column('direc', width=80, stretch=tk.NO)
		self.tree.column('message', width=800, stretch=tk.YES)

	def answer_connect_ok(self, *args, **kargs):
		super().answer_connect_ok(*args, **kargs)
		self.waitfor(self.ask_action('central', 'bus_list'), callback=self.answer_list_compo)
				
	def answer_list_compo(self, *mylist):
		print("CONNECTION", mylist)
		if 'central' not in mylist:
			mylist+=('central',)
		self.l_compo = mylist
		self.maj_combo()
			
	def maj_combo(self):
		list = ['all']
		
		list += sorted(self.l_compo)
		self.combo_cpn['values']=list

	def close_window(self):
		self.running = False

	def resize(self, event):
		#au cas ou il y a plusieurs resize, on temporise avec un index + 1 délai pour voir
		self.index_resize +=1
		#self.after(200, self.resize_window)

	def resize_window(self):
		self.index_resize -= 1
		#apres 200ms, est-ce qu'on est la derniere demande de re-dimensionnement ?
		if self.index_resize == 0:
			self.tree.column('time', width=150)
			self.tree.column('component', width=120)
			self.tree.column('level', width=40)
			self.tree.column('direc', width=80)
			self.tree.column('message', width=800)
			print("resize")

	def select_component(self, event=None):
		self.tree.delete(*self.tree.get_children())
		self.cpn_selected = self.combo_cpn.get()
		for q in self.liste_log:
			for log in q:
				self.display(log)

	def select_level(self, event=None):
		self.level = self.levels.index(int(self.combo_lvl.get()))
		self.tree.delete(*self.tree.get_children())
		for q in self.liste_log:
			for log in q:
				self.display(log)

	def process_in_log(self):
		if 'connect_log' not in self.__dict__ or self.connect_log is None:
			#print("not yet", list(self.__dict__))
			#print("not yet2", list(self.exposed_actions))
			#print("==")
			return
		log = self.connect_log.next_received()
		bappend = False
		cpt = 0
		delatt = 0
		lastt = None
		while log is not None:
			lastt = log.time			
			cpt +=1
			
			if log.name not in self.l_compo:
				self.l_compo+=(log.name,)
				self.maj_combo()

			if self.time_log is None or (self.time_log + 30) < log.time:
				q = deque()
				self.liste_log.append(q)
				self.time_log = log.time
			else:
				q = self.liste_log[-1]
				
			while len(self.liste_log)>4:
				#on supprime le 5eme element
				self.liste_log.pop(0)
				
			q.append(log)
			self.display(log)
			
			log = self.connect_log.next_received()
			
		if cpt>0:
			deltat = time.time() - lastt
			Log.send("TIME DRIFT :{}".format(deltat), level=3, direction="INTERNAL")

	def display(self, log):
		if self.cpn_selected=='all' or self.cpn_selected == log.name:
			ilevel = self.levels.index(log.level)
			if ilevel <= self.level:
				direc = 'unknown'
				if 'direction' in log.__dict__:
					direc = log.direction
				myt=time.strftime('%H:%M:%S', time.localtime(log.time))+(str(log.time%1)+"000")[1:5]
				self.tree.insert("", tk.END, values=(myt, log.name, log.level, direc, log.msg))
				self.tree.yview_moveto(1)
			else:
				#print("bypassed", ilevel, self.level, log.name)
				pass
		

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

		
	appli = app(HOST, PORT)
	keypress = kb_func()
	while keypress != 'q' and appli.running:
		## les commandes claviers
			
		keypress = kb_func()	
		if keypress and keypress == 'q':
			print("sortie")
			appli.quit()
		elif keypress and keypress == 'a':
			print(appli.connect_central.isconnected())
		elif keypress and keypress == 'z':
			print("Reconnexion au central")
			appli.reconnect()
		elif keypress and keypress == 't':
			print("Marqueur")

		#les echanges socket
		appli.do_service_process()
		appli.process_in_log()
		#time.sleep(0.01)		
		#print(plt.get_current_fig_manager().window.__dict__)
		#app.update_idle_tasks()
		appli.update()
