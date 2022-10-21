import json
import zlib

			
class Message:
	def __init__(self, **karg):
		for k in karg:
			self.__dict__[k] = karg[k]		
			
	def encode_simple(whatever):
		#Si ce n'est pas une chaine de charactère
		if not isinstance(whatever, str):
			whatever = whatever.to_json()

		# Si c'est une chaine de charactère
		if isinstance(whatever, str):
			return whatever.encode('utf-8')
		#Sinon on retourne une erreur
		else:
			print("error1**", whatever, type(whatever))


	def decode_simple(whatever):
		if isinstance(whatever, bytes):
			whatever = whatever.decode()
			
		if isinstance(whatever, str):
			if whatever!='':
				return json.loads(whatever)
			else:
				return None
		else:
			print("error2", whatever, type(whatever))
			return whatever
			
	def encode_compress(whatever):				
		if not isinstance(whatever, str):
			whatever = whatever.to_json()
		
		if isinstance(whatever, str):
			return zlib.compress(whatever.encode(), 1)
			#return whatever.encode()
		else:
			print("error1*", whatever, type(whatever))
	
	def decode_compress(whatever):
		if isinstance(whatever, bytes):
			whatever = zlib.decompress(whatever).decode()
		if isinstance(whatever, str):
			if whatever!='':
				return json.loads(whatever)
			else:
				return None
		else:
			print("error2", whatever, type(whatever))
			return whatever
			
	def selftrusted(self):
		return False

	def __str__(self):
		return json.dumps(self.__dict__)
		
	def to_json(self):
		return json.dumps(self.__dict__)
		
class MsgCmd(Message):
	def __init__(self, *, id, name, exp, **karg):
		Message.__init__(self, id=id, name=name, exp=exp, **karg)
		
	def encode(whatever):
		return Message.encode_simple(whatever.to_json())
	def decode(whatever):
		dic = Message.decode_simple(whatever)
		return MsgCmd(**dic)
	def selftrusted(self):
		#on autorise subs quoi qu'il en soit
		if self.name == 'bus_subs':
			return True
		else:
			return False
	
class MsgData(Message):
	def __init__(self, *, name, time, val, **karg):
		Message.__init__(self, name=name, time=time, val=val, **karg)
	def encode(whatever):
		return Message.encode_compress(whatever.to_json())
	def decode(whatever):
		elem = Message.decode_compress(whatever)
		msg = MsgData(**elem)
		return msg

class MsgLog(Message):
	def __init__(self, *, time, name, direction, level, msg, **karg):
		Message.__init__(self, time=time, name=name, direction=direction, level=level, msg=msg, **karg)
	def encode(whatever):
		return Message.encode_compress(whatever.to_json())
	def decode(whatever):
		elem = Message.decode_compress(whatever)
		msg = MsgLog(**elem)
		return msg
