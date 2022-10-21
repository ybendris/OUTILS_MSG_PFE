import tkinter as tk
from tkinter import ttk
from functools import partial
from subprocess import Popen, PIPE
import os.path
import traceback

from lib_netitem import NetworkItem
from lib_log import Log

	
class MonApp(NetworkItem, tk.Tk):
	def __init__(self, name, hote, port):
		tk.Tk.__init__(self)
		NetworkItem.__init__(self, name, hote, port)	
		self.protocol('WM_DELETE_WINDOW', self.close_window)
		self.init_gui()
		self.reconnect()
		
	def answer_connect_ok(self, *karg):
		#surcharge connection au central
		self.ask_services()
				
	def ask_services(self):
		self.waitfor(self.ask_action('central', 'bus_list'), callback=self.answer_fill_services)
		
	def ask_listactions(self, service):
		self.waitfor(self.ask_action(service, 'svc_list_actions'), callback=partial(self.answer_fill_actions, service=service))
		
	def close_window(self):
		self.running = False
		
	def init_gui(self):
		self.option_add('*Font', ('',10))
		self.minsize(450,0)
		#icone = "test.ico"
		
		bg = None

		#on change l'icone de l'application
		'''
		if not os.path.exists(icone):
			icone = os.path.join(chemin_script, icone)
		app.iconbitmap(icone)
		'''
		
		self.framev = tk.Frame(self, bg=bg)
		self.framev.pack(fill="y", padx=10, pady=10, ipady=10, expand=True)
		
		self.label_top = tk.Label(self.framev, text="SERVICES")
		self.label_top.pack()
		
		self.frame1 = tk.Frame(self.framev, bg=bg)
		self.frame1.pack(fill="x", padx=10, pady=10, ipady=10, expand=True)

		self.label_srv = tk.Label(self.framev, text="")
		self.label_srv.pack()
		
		
		self.frame2 = tk.Frame(self.framev, bg=bg)
		self.frame2.pack(fill="both", padx=10, pady=10, ipady=10, expand=True)


	def exec_action(self, srv, action):
		self.waitfor(self.ask_action(srv, action), callback=self.ok)

	def ok(self, *param):
		print("ok", param)
	
	def answer_fill_actions(self, *list_act, service):
		self.label_srv.config(text = service)
		print(list_act)
		
		#on supprime d'abord les anciens services
		for child in self.frame2.winfo_children():
			child.destroy()
			
		list_but = []
		
		for a in list_act:
			list_but.append(tk.Button(self.frame2, text="{}".format(a), command=partial(self.exec_action, service, a)))
			
		r = 0
		c = 0
		for b in list_but:
			b.grid(row=r, column=c)
			c += 1
			if c > 4:
				c = 0
				r += 1
			
	
	

	def answer_fill_services(self, *list_srv):
		Log.send("ASK SVC", level=1, direction="START")
		self.label_srv.config(text = '')
		print("LIST=", list_srv)
		#on supprime d'abord les anciens services
		for child in self.frame1.winfo_children():
			child.destroy()

		#on supprime d'abord les anciens services
		for child in self.frame2.winfo_children():
			child.destroy()
			
		list_but = []
		
		#but = tk.Button(frame_1, text="Refresh", command=partial(browse_file, process_name, p, cfg, file_path))
		list_but.append(tk.Button(self.frame1, text="Refresh", command=self.ask_services, bg='yellow'))
		
		#on demande à central tous les services
		for s in list_srv:
			list_but.append(tk.Button(self.frame1, text="{}".format(s), command=partial(self.ask_listactions, s)))
			
		r = 0
		c = 0
		for b in list_but:
			b.grid(row=r, column=c)
			c += 1
			if c > 4:
				c = 0
				r += 1
	
	
	

#============================================
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

	opts, args = getopt.getopt(sys.argv[1:], "")
	
	chemin_script = os.path.dirname(sys.argv[0])
	nom_script = os.path.splitext(os.path.basename(sys.argv[0]))[0]

	HOST = '127.0.0.1'	# The server's hostname or IP address
	PORT = 65432		# The port used by the server
	
	appli = MonApp('appli_ctrl', HOST, PORT)		
	
	srv = None

	keypress = kb_func()
	#appli.after(50, appli.ask_services)
	while keypress != 'q' and appli.running:
		## les commandes claviers
			
		keypress = kb_func()	
		if keypress and keypress == 'a':
			print(appli.connect_central.isconnected())
		elif keypress and keypress == 'z':
			print("Reconnexion au central")
			appli.reconnect()
		elif keypress and keypress == 'r':
			print("Dmd composants")
			appli.ask_services()
		

		#les echanges socket
		appli.do_service_process()
		#time.sleep(0.01)		
		#print(plt.get_current_fig_manager().window.__dict__)
		#app.update_idle_tasks()
		appli.update()

	
	#app.mainloop()
	'''
	try
		pass
	except Exception as e:
		print("ERROR", e, file=sys.stderr)
		print(traceback.format_exc())
	'''