# -*- coding: utf-8 -*-
import time		
from functools import partial

from lib_connector import Connector, CmdConnector, LogConnector

from lib_log import Log
from lib_msg import MsgCmd


class ClientNet:
	def __init__(self):
		self._waitfor = {}
		self.no_msg = 0

	def ask_action(self, dest, cmd, *param, **kparam):
		id = self.idauto()
		self.send_cmd(id, dest, cmd, *param, **kparam)		
		Log.send("CMD {} / cmd id {} dest {} cmd {}".format(self.name, id, dest, cmd), level=1, direction="EXEC-OUT")
		return id		
		
	def waitfor(self, id, *args, callback):
		self._waitfor[id] = {'callback':callback}
					
	def respond(self, id, response):
		#reponse attendue
		if isinstance(response,dict) and 'cr' in response and response['cr']==False:
			Log.send("Error in execution {} = {}".format(id, response), level=1, direction="EXEC-END")
			return False
		elif id in self._waitfor:
			Log.send("Retreive expected answ id {} = {}".format(id, response), level=1, direction="EXEC-END")
			wait = self._waitfor[id]
			del self._waitfor[id]
			ma_fonc = wait['callback']
			if isinstance(response, dict):
				ma_fonc(**response)
			elif isinstance(response, list):
				ma_fonc(*response)
			else:
				ma_fonc(response)
			return True
		#reponse non attendue
		else:
			Log.send("Retreive answ id {} = {}".format(id, response), level=1, direction="EXEC-END")
			return False

	def idauto(self):
		self.no_msg += 1
		return "{:04d}{}".format(self.no_msg,self.name)

#*************************************************


class ServerNet:
	def __init__(self):
		self.exposed_actions = {}
		self.requests = []
		self.record_action('svc_list_actions', 'short', self.action_list_actions)
		
	def record_action(self, name, rtype, callback):
		"""
			enregistrement d'une action exposee par le service
			on donne un callback = fonction a appeler pour executer l'action
			rtype peut valoir : long, short
		"""
		self.exposed_actions[name] = { 'name':name, 'rtype':rtype, 'callback':callback }	
		
	def action_list_actions(self, *param):
		return list(self.exposed_actions)

	def is_action_short(self, op_name):
		if op_name in self.exposed_actions:
			return self.exposed_actions[op_name]['rtype']!="long"
	
	def execute_action(self, request):
		op_name = request.name
		if op_name in self.exposed_actions:
			ma_fonction = self.exposed_actions[op_name]['callback']
			retour = ma_fonction(op_name, request, *request.param, **request.kparam)
			Log.send("From {}, Exec {}, Id {} / Param {}{}".format(request.exp, request.name, request.id, request.param, request.kparam), level=1, direction="EXEC")
			return retour
		else:
			Log.send("From {}/ Unknown exec {}, Id {}".format(request.exp, request.name, request.id), level=1, direction="EXEC")
			return {'cr':False}

	def manage_action_msg(self, msg):
		"""
		try:
			if super().manage_action_msg(msg):
				return True
		except:
			pass
		"""

		if msg is None or msg.name == 'answ':
			return False
			
		elif self.is_action_short(msg.name):
			#si la commande est une simple demande (get) elle est executee immediatement
			res= self.execute_action(msg)
			print("CHECK1 {}={}".format(msg.name, res))
			self.reply(request=msg, answer=res)
			return True
			
		else:
			Log.send("SRV {} : {}/ cmd stacked {} {}".format(self.name, msg.dest, msg.id, msg.name), level=2, direction="EXEC")
			#sinon elle est ajoutee a la liste des requetes
			if 'requests' not in self.__dict__ or self.requests is None:
				self.requests = []
			self.requests.append(msg)
			return True
			
	def next_action(self):
		if self.requests:
			msg = self.requests.pop(0)
			Log.send("SRV {}/ cmd unstacked {} {}".format(self.name, msg.id, msg.name), level=2, direction="EXEC")
			self.reply(request=msg, answer=self.execute_action(msg))			

	def nb_actions_pending(self):
		return len(self.requests)

	def reply(self, request, answer):
		if answer is not None:
			Log.send("To {}, answer id {} = {}".format(request.exp, request.id, answer), level=2, direction="EXEC")
			return self.send_cmd(request.id, request.exp, 'answ', answer)
		else:
			Log.send("To {}, answer id {}".format(request.exp, request.id), level=2, direction="EXEC")
			return self.send_cmd(request.id, request.exp, 'answ')

	def send_cmd(self, id, dest, cmd, *param, **kparam):
		if len(param) == 1:
			msg = MsgCmd(id=id, name=cmd, exp=self.name, dest=dest, param=param[0], kparam=kparam)
		else:
			msg = MsgCmd(id=id, name=cmd, exp=self.name, dest=dest, param=param, kparam=kparam)
		
		self.connect_cmd.send(msg)


#*************************************************
#
#*************************************************

class SrvManagement:
	def set_connection(self, b_producer, item, TypeConnector, params=None):
		self.__dict__['{}_params'.format(item)] = params
		if b_producer:
			self.record_action("svc_producer_{}".format(item), "short", partial(self.action_central_connect_other, item=item, direction="out", TypeConnector=TypeConnector))		
		else:
			self.record_action("svc_consumer_{}".format(item), "short", partial(self.action_central_connect_other, item=item, direction="in", TypeConnector=TypeConnector))
		
				
	def action_central_connect_other(self, cmd, msg, *, item, direction, TypeConnector, host, peer):
		conn_name = 'connect_{}'.format(item)
		connector = None
		
		if conn_name in self.__dict__:
			connector = self.__dict__[conn_name]
			print("connection existante:", connector.conn.get_host(), host, connector.conn.get_peer(), peer)
			
		if connector is None or connector.conn.get_host()!=host or connector.conn.get_peer()!=peer or not connector.conn.isconnected():
			connector = TypeConnector(host, peer, False)
			self.__dict__[conn_name] = connector
			connector.granted('main', direction=direction)
			#on attend une fraction de seconde de sorte que la connexion data soit établie
			#######
			time.sleep(0.1)
			
		host, peer = connector.getsockname()
		return {'name':self.name, 'host':host, 'peer':peer, 'params':self.__dict__['{}_params'.format(item)]}


#*************************************************
#
#*************************************************


class NetworkItem(ServerNet, ClientNet, SrvManagement):
	def __init__(self, name, hote, port):
		ClientNet.__init__(self)
		ServerNet.__init__(self)
		self.set_connection(True, 'log', LogConnector)
		Log.define(self)
		self.running = True
		self.connect_cmd = None
		self.name = name
		self.peername = (hote, port)
		#on mettra ici le connecteur pour diffuser les données
		self.record_action("svc_stop", "short", self.action_stop) #n'existe pas		
		self.record_action("svc_log_level", "short", self.action_log_level)
		
	def reconnect(self):
		self.connect_cmd = CmdConnector(*self.peername)
		#on s'enregistre = SUBSCRIBE
		if self.connect_cmd.isconnected():
			self.connect_cmd.granted("main")
			host, peer = self.connect_cmd.getsockname()
			self.waitfor(self.ask_action("central", 'bus_subs', name=self.name, host=host, peer=peer, actions=list(self.exposed_actions)), callback=self.answer_connect_ok)
		
	def get_received(self):
		msg = self.connect_cmd.next_received()
		while msg is not None:
			if msg.name == 'answ':
				if not self.respond(msg.id, msg.param):
					#reponse reçu pour un appel non référencé
					Log.send("CPNT {} / KO ANSWER ID {} UNKNOWN".format(self.name, msg.id), level=3, direction="ERROR")
			else:
				self.manage_action_msg(msg)
			msg = self.connect_cmd.next_received()
		
	def do_service_process(self):
		#on cherche tous les connecteurs reliés self
		for e in self.__dict__:
			if isinstance(self.__dict__[e], Connector):
				conn = self.__dict__[e]
				conn.inout()
		
		#reception central
		self.get_received()

		#on traite les messages en attente : tous prioritaires
		while self.nb_actions_pending()>0:
			self.next_action()
		
		
	def action_stop(self, *args, **kargs):
		self.running = False
				
	def answer_connect_ok(self, *args, **kargs):
		print("OK", args, kargs)
		
	def answer_ok(self, *args, **kargs):
		print("OK", args, kargs)

	def action_log_level(self, cmd, msg, *karg):
		Log.filter(int(msg.param))

			
## ===================================
## ===================================

if __name__ == '__main__':
	import sys
	import getopt
	import msvcrt
	from functools import partial
	
	class ServiceTest(NetworkItem):							
		def __init__(self, name, hote, port):
			NetworkItem.__init__(self, name, hote, port)
			self.record_action("svc_test_scalar", "short", self.action_test_scalar)
			self.record_action("svc_test_dict", "short", self.action_test_dict)

		def ask_test_scalar(self, dest):
			self.waitfor(self.ask_action(dest, 'svc_test_scalar', "arg1", "arg2", "arg3", toto="titi"), callback=partial(self.answer_test, pback='info_complement'))

		def ask_test_dict(self, dest):
			self.waitfor(self.ask_action(dest, 'svc_test_dict', "arg1", "arg2", "arg3", toto="titi"), callback=partial(self.answer_test, pback='info_complement'))
			
		def ask_list(self):
			self.waitfor(self.ask_action("central", 'bus_list', "arg1", "arg2", "arg3", toto="titi"), callback=partial(self.answer_test, pback='bof'))
		
		def action_test_scalar(self, cmd, msg, *args, **kargs):
			print("ACTION TEST")
			print("MSG=", str(msg))
			print("ARGS=", args)
			print("KARGS=", kargs)
			print("----------")
			return "bonjour"
			return {'tata':12, 'toto':48}

		def action_test_dict(self, cmd, msg, *args, **kargs):
			print("ACTION TEST")
			print("MSG=", str(msg))
			print("ARGS=", args)
			print("KARGS=", kargs)
			print("----------")
			return {'tata':12, 'toto':48}
		
		
		def answer_test(self, *args, pback=None, **kargs):
			print("ANSWER TEST")
			#print("response=", response)
			print("args=", args)
			print("pback=", pback)
			print("kargs=", kargs)
			print("----------")		
	
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
	name2 = args[1]
	test = ServiceTest(name, HOST, PORT)




	keypress = kb_func()		
	while keypress != 'q':			
		## les commandes claviers
		if keypress and keypress == 'a':
			print(test.connect_cmd.isconnected())
		elif keypress and keypress == 'z':
			test.reconnect()
		elif keypress and keypress == 'y':
			test.ask_test_scalar(name2)
		elif keypress and keypress == 'u':
			test.ask_test_dict(name2)
		elif keypress and keypress == 'i':
			test.ask_list()
		'''
		elif keypress and keypress == 'e':
			#test.send(test.idauto(), "essai", 'invk', "toto")
			pass
		elif keypress and keypress == 'r':
			test.waitfor(test.ask_action('central', 'bus_newpeer'), callback=test.answer_startdatapoolsocket)
		elif keypress and keypress == 't':
			test.waitfor(test.ask_action('central', 'bus_list'), callback=test.answer_connect_all)
		'''
			
		keypress = kb_func()	

		#les echanges socket
		test.do_service_process()
