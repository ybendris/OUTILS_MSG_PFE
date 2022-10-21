import socket
import selectors

from lib_log import Log

class Connection:
	SEP = "[---]"
	def __init__(self, host, port, obj, events = selectors.EVENT_READ | selectors.EVENT_WRITE):
		self._server_addr = (host, port)
		self._buffer = {}
		self._separator = Connection.SEP.encode()
		self._selector = selectors.DefaultSelector()
		
	def get_host(self):
		return self._server_addr[0]
		
	def get_peer(self):
		return self._server_addr[1]
		
	def selector(self):
		return self._selector
	
	def service_connection(self, key, mask):
		sock = key.fileobj
		obj = key.data
		if self.isconnected() and not sock._closed and mask & selectors.EVENT_READ:
			try:
				recv_data = sock.recv(1024*1024)	 # Should be ready to read
			except:
				print("CN/socket fermée/recv R", sock._closed)
				self._selector.unregister(sock)
				obj.close(sock)
				del self._buffer[sock]
				return False
			else:
				if recv_data:
					#reliquat
					capture0 = self._buffer[sock]
					self._buffer[sock] += recv_data
					capture = self._buffer[sock]
					#on fait attention a ne pas bloquer la machine
					cpt = 0
					fin = self._buffer[sock].find(self._separator)
					while fin > -1 and cpt < 30:
						#le prochain message à decrypter
						recv_data = self._buffer[sock][:fin]
						#appel obj->receive
						obj.receive(sock, recv_data)
						try:
							pass
						except:
							print("pb receive with")
							print("0=", capture0)
							print("1=", capture)
							print("2=", recv_data)
							pass
						#print('CN/received {}bytes from connection'.format(len(recv_data)), sock.getpeername())
						#le reste
						reste = self._buffer[sock][fin+len(self._separator):]
						self._buffer[sock] = reste
						fin = self._buffer[sock].find(self._separator)
						cpt+=1
					if fin > -1:
						Log.send("engorgement des messages")
				else:
					print('closing connection', sock.getpeername())
					self._selector.unregister(sock)
					sock.close()
					#appel obj->close
					obj.close(sock)
					del self._buffer[sock]
					
		if self.isconnected() and not sock._closed and mask & selectors.EVENT_WRITE:
			#appel obj->to_send
			to_send = obj.to_send(sock)
			while to_send is not None:
				##print('sending {}'.format(repr(to_send)), 'to connection', sock.getpeername())					
				#print('CN/sending {}bytes to connection'.format(len(to_send)), sock.getpeername())					
				try:
					sent = sock.send(to_send+self._separator)	 # Should be ready to write
				except:
					print("CN/socket fermée/sent W", sock._closed)
					self._selector.unregister(sock)
					obj.close(sock)
					del self._buffer[sock]
					return False
				to_send = obj.to_send(sock)
					
		return True
				
	def isconnected(self):
		return False
		
	
class ConnectionClient(Connection):
	##OBJ doit avoir quatre methodes : 
	## * open(self, socket)
	## * reveive(self, socket, buff)  avec buff des bytes
	## * to_send(self, socket)=>renvoie des bytes 
	## * close(self, socket)
	def __init__(self, host, port, obj, events = selectors.EVENT_READ | selectors.EVENT_WRITE):
		super().__init__(host, port, obj, events)		
		print('starting connection to', self._server_addr)	
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._lsocket = sock
		#sock.setblocking(False)
		self._connected = sock.connect_ex(self._server_addr)==0
		self._selector.register(sock, events, data=obj)
		if self._connected:
			#appel obj->open
			obj.open(sock)
			self._buffer[sock]="".encode()

	def service_connection(self, key, mask):
		cr = super().service_connection(key, mask)
		if not cr:
			self._connected = False
		return cr			
		
	def isconnected(self):
		return not self._lsocket._closed and self._connected
		
						
		
class ConnectionPool(Connection):
	##OBJ doit avoir trois methodes : 
	## * reveive(self, socket, buff)  avec buff des bytes
	## * to_send(self, socket)=>renvoie des bytes 
	## * open(self, socket)
	## * close(self)
	def __init__(self, host, port, obj, events = selectors.EVENT_READ | selectors.EVENT_WRITE):
		super().__init__(host, port, obj, events)
		self._lsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._lsocket.setblocking(False)
		
		#listen for incoming connections
		self._lsocket.bind(self._server_addr)
		self._lsocket.listen()
		self._selector.register(self._lsocket, selectors.EVENT_READ, data=None)
		self._spc_obj = obj
		self._spc_events = events

	def isconnected(self):
		return not self._lsocket._closed
	
	def accept_wrapper(self):
		sock, addr = self._lsocket.accept()  # Should be ready to read
		print('accepted connection from', addr)
		sock.setblocking(False)
		obj = self._spc_obj		
		#appel obj->open
		print("CN/open socket", type(obj))
		obj.open(sock)
		events = selectors.EVENT_READ | selectors.EVENT_WRITE
		self._selector.register(sock, self._spc_events, data=obj)
		print('accept', sock.getpeername())
		self._buffer[sock]="".encode()

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

	class GestTest:
		def __init__(self):
			self.sok = {}
			
		def open(self, sock):
			print("LIAISON OK")
			self.sok[sock] = {'in':[], 'out':[]}
			
		def close(self, sock):
			del self.sok[sock]
			
		def receive(self, sock, binaire):
			self.sok[sock]['in'].append(binaire.decode())
			
		def to_send(self, sock):
			if sock in self.sok and self.sok[sock]['out']:
				return self.sok[sock]['out'].pop(0).encode()
				
		def remplit(self, str):
			for sock in self.sok:
				for i in range(20):
					self.sok[sock]['out'].append("{} / {} => {}".format(str, sock.getsockname(), i))
					
		def affiche(self):
			for sock in self.sok:
				print(sock.getsockname())
				for s in self.sok[sock]['in']:
					print(s)
				print()
	
	opts, args = getopt.getopt(sys.argv[1:], "s")
	
	HOST = '127.0.0.1'	# The server's hostname or IP address
	PORT = 65432		# The port used by the server
	
	dopts = dict(opts)

	mytest = GestTest()
	if '-s' in dopts:
		#server
		conn = ConnectionPool(HOST, PORT, mytest)
		
	else:
		conn = ConnectionClient(HOST, PORT, mytest)
		
	keypress = kb_func()		
	while conn.isconnected() and keypress != 'q':			
		## les commandes claviers
		if keypress and keypress == 'a':
			print(mytest.sok)
		elif keypress and keypress == 'z':
			mytest.remplit('essai')
		elif keypress and keypress == 'e':
			mytest.affiche()
		keypress = kb_func()	

		#les echanges socket
		events = conn.sel.select(timeout=0)
		for key, mask in events:
			if '-s' in dopts and key.data is None:
				conn.accept_wrapper()
			else:
				conn.service_connection(key, mask)
				
		