from lib_connection import ConnectionPool, ConnectionClient
from lib_msg import MsgCmd, MsgData, MsgLog
from collections import deque
from lib_log import Log
import selectors


class Connector:
	def __init__(self, name, host, port, class_msg, server_sock=False):
		self.name = name
		self.class_msg = class_msg
		self.server_sock = server_sock #mode server or not
		self.sok = {}  #liste des connexions socket
		self.peername = {}
		if self.server_sock:
			self.conn = ConnectionPool(host, port, self)
		else:
			self.conn = ConnectionClient(host, port, self)
		#on met tout ce qui arrive dans inrecup
		self.inrecup = deque()
		self.allow_out = {}
		self.allow_in = {}
		
	def get_sockaddress(self):
		return {'host':self.conn.get_host(), 'peer':self.conn.get_peer()}
			
	def granted(self, name, sock=None, items=None, direction=None):
		if sock is None and len(self.sok)==1:
			sock = list(self.sok.keys())[0]
			
		if sock in self.sok:
			self.sok[sock]['name'] = name
			self.peername[name] = {'sok':sock, 'items':items}
			
		if direction is not None and (direction == "in" or direction == "out" or direction == "both") :
			if direction == "in" or direction == "both":
				self.allow_in[sock] = True
			if direction == "out" or direction == "both":
				self.allow_out[sock] = True
								
	def granted_peername(self, name, host, peer, items, direction=None):
		b_found = False
		peername = [host, peer]
		for sock in self.sok:			
			if list(sock.getpeername()) == list(peername):
				b_found = True
				self.granted(name, sock, items, direction)
				Log.send("CONNECTOR {} / Granted accepted {}:{} among {} sockets".format(name, name, peername, len(self.sok)), level=1, direction="RECEIVE")
				break
		if not b_found:
			Log.send("CONNECTOR {} / Granted rejected {}:{} among {} sockets".format(self.name, name, peername, len(self.sok)), level=1, direction="RECEIVE")
			print(peername)
			for sock in self.sok:			
				print("!=",sock.getpeername())
			return False
		
		return True

	def open(self, sock):		
		self.sok[sock] = {'out':deque()}
		
	def close(self, sock):
		b_find = False
		if sock in self.sok:
			b_find = True
			del self.sok[sock]
		#dans tous les cas on verifie
		self.check_sock(sock)
		return b_find
		
	##nécessaire pour la gestion bas-niveau sock
	def receive(self, sock, binaire):
		msg = self.class_msg.decode(binaire)
		if sock in self.sok and 'name' in  self.sok[sock] or msg.selftrusted():
			Log.send("CONNECTOR {} / RECEIVE OK {}".format(self.name, msg), level=3, direction="RECEIVE")
			self.inrecup.append(msg)
		else:
			Log.send("ERROR CONNECTOR {} / RECEIVE UNTRUSTED {}".format(self.name, msg), level=2, direction="RECEIVE")
			pass
		
	##nécessaire pour la gestion bas-niveau sock
	def to_send(self, sock):
		if sock in self.sok and self.sok[sock]['out']:
			msg = self.sok[sock]['out'].popleft()
			return self.class_msg.encode(msg)
		
	##pour le pilotage
	def next_received(self):
		if self.inrecup:
			return self.inrecup.popleft()
					
	##pour le pilotage
	def send(self, msg):		
		#a surcharger
		pass
			
	def inout(self):
		if self.isconnected():
			events = self.conn.selector().select(timeout=0)
			for key, mask in events:
				if self.server_sock and key.data is None:
					self.conn.accept_wrapper()
				else:
					#QUESTION : comment vérifie-t-on que le socket qui envoie est bien déclaré en envoie i.e. "allow_in", ici pas de socket ?
					#REPONSE
					#sock = key.fileobj
					#allow_in seulement pour ConnectorData et ConnectorLog pour l'instant
					sock = key.fileobj
					"""
					if sock in self.allow_in and mask & selectors.EVENT_READ:
						#print("get in ?", type(self), mask & selectors.EVENT_READ, mask & selectors.EVENT_WRITE)
						self.conn.service_connection(key, mask)
					if sock in self.allow_out and mask & selectors.EVENT_WRITE:
						#print("get out ?", type(self), mask & selectors.EVENT_READ, mask & selectors.EVENT_WRITE)
						self.conn.service_connection(key, mask)
					#marche pas :( <= des cas ne sont pas couverts
					"""
					#print(type(self), "INOUT", mask & selectors.EVENT_READ > 0, sock in self.allow_in, mask & selectors.EVENT_WRITE > 0, sock in self.allow_out)
					self.conn.service_connection(key, mask)
				
	def isconnected(self):
		return self.conn.isconnected()

	def getsockname(self):
		"""
		if 'main' not in self.peername and len(self.sok)==1:
			for sock in self.sok:
				self.peername['main']={'sok':sock}
		"""
		if 'main' in self.peername:
			return self.peername['main']['sok'].getsockname()
		else:
			return self.conn._server_addr
				
	def check_sock(self, sok=None):
		#purge de la liste des sockets
		for name in self.peername.copy():
			if sok is not None and self.peername[name]['sok']==sok or self.peername[name]['sok'] not in self.sok:
				del self.peername[name]
		
		
class CmdConnector(Connector):
	def __init__(self, host, port, server=False):
		Connector.__init__(self, 'CON-CMD', host, port, MsgCmd, server)

	def granted(self, name, sock=None, items=None, direction="both"):
		Connector.granted(self, name, sock, items, direction)
		
	##pour le pilotage
	def send(self, msg):		
		if 'sock' in msg.__dict__:
			#test a supprimer  ?
			print("PB WITH SOCK")
			del msg.__dict__['sock']
			
		sock = None
		if msg.dest in self.peername:
			sock = self.peername[msg.dest]['sok']
		elif 'main' in self.peername:
			sock = self.peername['main']['sok']
			
		if sock is not None:
			self.sok[sock]['out'].append(msg)
		else:			
			Log.send("Error CONNECTOR {} / KO Sock Destinataire {} non trouvé".format(self.name, msg.dest), level=1, direction="SEND")
	
class DataConnector(Connector):
	def __init__(self, host, port, server=False):
		Connector.__init__(self, 'CON-DATA', host, port, MsgData, server)
		self.matrixout = {}
		self.matrixin = {}

	def granted(self, name, sock=None, items=None, direction=None):
		if sock is None and len(self.sok)==1:
			sock = list(self.sok.keys())[0]
		Connector.granted(self, name, sock, items, direction)

		if direction is not None and (direction == "in" or direction == "out") :

			if items is not None:
				if not isinstance(items, list):
					items = [items]
				for i in items:
					if direction == "out":
						#matrixout
						if i not in self.matrixout:
							self.matrixout[i] = []
						self.matrixout[i].append(sock)
					else:
						#matrixin
						if '*' not in i:				
							listitems = ['*', i]
							if i.find('.')>0:
								listitems.append("{}.*".format(i[:i.find('.')]))
							self.matrixin[i] = listitems				
		
	##pour le pilotage
	def send_to_one(self, name, msg):
		if name in self.peername:
			sock = self.peername[name]['sok']
			self.sok[sock]['out'].append(msg)

	def send(self, msg, profil=None):
		b_sent = False
		#
		if len(self.sok)==0:
			pass
		elif profil is None and len(self.matrixout)==0:
			for sock in self.sok:
				#il faut que sock soit demandeur
				if sock in self.allow_out:					
					#print("DIF DATA", len(self.sok), len(self.allow_out))
					try:
						self.sok[sock]['out'].append(msg)
						b_sent = True
					except:
						print("ERREUR SOCK FERMEE!")
		else:
			listitems = profil			
			if listitems is None:
				listitems = ['*', msg.name]
				if msg.name.find('.')>0:
					listitems.append("{}.*".format(msg.name[:msg.name.find('.')]))
			
			for i in listitems:
				if i in self.matrixout:
					for sock in self.matrixout[i]:
						try:
							self.sok[sock]['out'].append(msg)
							b_sent = True
						except:
							print("ERREUR SOCK FERMEE!")
							
		return b_sent

	def check_sock(self, sok=None):
		Connector.check_sock(self, sok)
		
		if sok is not None:
			#on purge la matrice
			for i in self.matrixout:
				if sok in self.matrixout[i]:
					self.matrixout[i].remove(sok)
	
class LogConnector(Connector):
	def __init__(self, host, port, server=False):
		Connector.__init__(self, 'CON-LOG', host, port, MsgLog, server)

	def granted(self, name, sock=None, items=None, direction=None):
		if sock is None and len(self.sok)==1:
			sock = list(self.sok.keys())[0]
		Connector.granted(self, name, sock, items, direction)
		
	##pour le pilotage
	def send_to_one(self, name, msg):
		if name in self.peername:
			sock = self.peername[name]['sok']
			self.sok[sock]['out'].append(msg)

	def send(self, msg):
		for sock in self.sok:
			if sock in self.allow_out and self.allow_out[sock]:
				self.sok[sock]['out'].append(msg)
	
