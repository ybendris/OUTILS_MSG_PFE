from lib_msg import MsgLog
import time

class Log:
	server = None
	level = 3
	
	def define(server):
		Log.server = server
	
	def filter(level):
		Log.level = level
		
	def send(*args, level=3, direction=None, **kwds):
		if Log.server is None or 'connect_log' not in Log.server.__dict__:
			if level<3:
				print(*args, **kwds)
		elif level <= Log.level:
			if isinstance(args, list):
				message = " ".join(args)
			else:
				message = args
			Log.server.connect_log.send(MsgLog(time=time.time(), name=Log.server.name, direction=direction, level=level, msg=message))