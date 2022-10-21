# -*- coding: utf-8 -*-
import time
from functools import partial
import re


from lib_log import Log
from lib_msg import MsgCmd
from lib_connector import Connector, CmdConnector, DataConnector, LogConnector
from lib_netitem import ServerNet, ClientNet, SrvManagement

class Bus(ServerNet, ClientNet):
	def __init__(self, host, peer):
		ServerNet.__init__(self)
		ClientNet.__init__(self)

		self.connect_cmd = CmdConnector(host, peer, True)
		self.name = "central"
		self.host = host
		self.peer = peer
		self.peercounter = 0
		self.record_action('bus_subs', "short", self.action_subscribe)
		self.record_action("bus_list", "short", self.action_list)
		Log.define(self)

		self.connect_data = DataConnector(self.host, self.allocate_peer(), True)
		self.connect_log = LogConnector(self.host, self.allocate_peer(), True)
					
	def init_connector(self, item, TypeConnector, action):
		connector = TypeConnector(self.host, self.allocate_peer(), True)
		self.__dict__['connect_{}_{}'.format(item, action)] = connector
		
	def allocate_peer(self):
		self.peercounter +=1
		return self.peer+self.peercounter
		
	def do_bus_process(self):
		##connexion avec central
		for e in self.__dict__:
			if isinstance(self.__dict__[e], Connector):
				conn = self.__dict__[e]
				conn.inout()
			
		##on traite ce qui est arrivé
		self.get_received_other('data')
		self.get_received_other('log')
		self.get_received_cmd()
		#on traite les messages en attente : tous prioritaires
		while self.nb_actions_pending()>0:
			self.next_action()
		
	def get_received_cmd(self):
	#gestion des messages de type CMD arrivant
	#
		msg = self.connect_cmd.next_received()
		while msg is not None:
			if msg.dest.lower() == self.name:
				Log.send("CENTRAL {}/ msg {} {} param {}".format(self.name, msg.id, msg.name, msg.param), level=3, direction="EXEC")
				#pour Central
				if msg.name == 'answ':
					if not self.respond(msg.id, msg.param):
						Log.send("CENTRAL {}/ ANSWER ID UNKNOWN {}".format(self.name, msg.id), level=3, direction="EXEC")
				else:
					#on regarde dans les actions enregistrees
					self.manage_action_msg(msg)
			else:
				#on redirige
				self.connect_cmd.send(msg)
				
			msg = self.connect_cmd.next_received()
				
	
	def get_received_other(self, item):
	#gestion des messages qutre que CMD arrivant
	#
		pipe = self.__dict__['connect_{}'.format(item)]
		msg = pipe.next_received()
		while msg is not None:
			if item == 'log':
				print(msg)
			#on filtre
			#on redirige
			#il faudrait recuperer le profil du message pour envoyer à la matrixout
			profil = None
			if 'matrixin' in pipe.__dict__ and msg.name in pipe.matrixin:
				profil = pipe.matrixin[msg.name]
				pipe.send(msg, profil)
			else:
				pipe.send(msg)
				
			msg = pipe.next_received()
			
	

	def action_subscribe(self, cmd, msg, name, host, peer, actions=[], item="cmd"):
	#lorsque qu'un acteur veut se referencer sur le bus
	#il expose ses actions
	#selon les actions exposées on cree des liens
		if name == msg.exp:
			Log.send("ACCREDITATION {}={}:{}".format(name, host, peer), level=3, direction="EXEC")			
			self.connect_cmd.granted_peername(name, host, peer, actions)
			
			#on passe toutes les actions en revue
			#benefice : Le bus controle tous les interlocuteurs
			#cela lui permettrait d'avoir une liste blanche ou une liste noire pour autoriser ou interdire des communications
			for action in actions:
				type = None
				direction = None

				#on demande automatiquement la connexion du canal si c'est producer ou consumer
				if re.search("^svc_producer_", action):
					type = action[len("svc_producer_"):]
					direction = "in"
					
				if re.search("^svc_consumer_", action):
					type = action[len("svc_consumer_"):]
					direction = "out"
					
				if type is not None:
					conn_name = 'connect_{}'.format(type)				
					if conn_name in self.__dict__:
						connector = self.__dict__[conn_name]
						host_item, peer_item = connector.getsockname()
						self.waitfor(self.ask_action(name, action, host=host_item, peer=peer_item), callback=partial(self.answer_record_provider, item=type, direction=direction))
						Log.send("DEMANDE CONNEXION {} FAITE".format(type), level=2, direction="EXEC")			
		else:
			Log.send("CENTRAL {}/ ERROR SUBSCRIBE {}!={}".format(self.name, msg.exp, name), level=3, direction="EXEC")
			return False
		
		return True		
		
	def answer_record_provider(self, *, item, direction, name, host, peer, params=None):
	#appelé une fois que la connexion est etablie suite à la demande svc_consumer_ ou svc_producer_ lancée
		Log.send("connection approved for {} {} {}".format(name, direction, item), level=2, direction="EXEC")			
		connector = self.__dict__['connect_{}'.format(item)]
		#un tri est fait au niveau de central => on donne params comme info
		connector.granted_peername(name, host, peer, params, direction)
		
	def action_list(self, cmd, msg, action=None, *args, **kargs):
		if action is None:
			print(list(self.connect_cmd.peername))
			self.connect_cmd.check_sock()
			print(list(self.connect_cmd.peername))
			return list(self.connect_cmd.peername)
		else:
			selected_srv = []
			for srv in self.connect_cmd.peername:
				#print("{} in {}:{} ?{}".format(action, srv, ", ".join(self.connect_cmd.peername[srv]['items']), action in self.connect_cmd.peername[srv]['items']))
				if action in self.connect_cmd.peername[srv]['items']:
					selected_srv.append(srv)
			#print("ask:{} => return:{}".format(action, ", ".join(selected_srv)))
			return selected_srv
		

## ===================================
## ===================================

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

	opts, args = getopt.getopt(sys.argv[1:], "s")
	
	test = Bus( HOST, PORT)



	keypress = kb_func()		
	while keypress != 'q':			
		## les commandes claviers
		if keypress and keypress == 'a':
			print(test.connect_cmd.isconnected())
		elif keypress and keypress == 'z':
			print(test.action_list())
		elif keypress and keypress == 'e':
			pass
		keypress = kb_func()	

		#les echanges socket
		test.do_bus_process()
		time.sleep(0.01)

