import sys
import getopt
import msvcrt

import time
import math

import random
from functools import partial

import numpy as np
from collections import deque

from lib_netitem import NetworkItem
from lib_msg import MsgData
from lib_log import Log

import glob
import os.path

"""
	Stub pour voir comment pourrait fonctionner un superviseur
"""
class ProcExec(NetworkItem):
	def __init__(self, name, hote, port):
		NetworkItem.__init__(self, name, hote, port)
		self.record_action('exe_execproc', 'long', self.action_execproc)
		for p in self.list_procedures():
			self.record_action('exe_execproc__{}'.format(p), 'long', partial(self.action_execproc, p))
		self.proc2exec = []
		self.encours = None
		self.reconnect()
				
	def action_execproc(self, proc, *karg):
		if self.encours is not None:
			self.proc2exec.append(proc)
		else:
			self.prepare_proc(proc)
			
	def list_procedures(self):
		return glob.glob("proc*.txt")
			
			
	def prepare_proc(self, maproc):
		Log.send("EXECUTION DE {}".format(maproc), level=2, direction="PROC")
		#on initialise le ctxt
		ctx = {'name' : maproc, 'pos':0, 'statements':self.charge_proc(maproc)}
		#on lance l'execution de la 1ere ligne
		self.encours = ctx
		self.execnextstatement()
			
	def charge_proc(self, name):
		statements = []
		with open(name, 'r') as file:
			for line in file:
				statements.append(line.rstrip())
			
		return statements
		
	def execnextstatement(self):
		ctx = self.encours
		#dernier statement
		#y-a-t-il une attente ?
		if 'wait' in ctx:
			if isinstance(ctx['wait'], float):
				t = time.perf_counter()
				if t >= ctx['wait']:
					Log.send("attente terminée".format(t, ctx['wait']), level=3, direction="wait")
					del ctx['wait']
					ctx['pos'] += 1
					
		elif ctx['pos'] < len(ctx['statements']):		
			statement = self.analyse_statement(ctx['statements'][ctx['pos']])
			while statement is None:
				Log.send(ctx['statements'][ctx['pos']], level=3, direction="pass")
				ctx['pos'] += 1
				if ctx['pos'] < len(ctx['statements']):
					statement = self.analyse_statement(ctx['statements'][ctx['pos']])
				else:
					break
								
			if statement is not None:
				Log.send(ctx['statements'][ctx['pos']], level=3, direction="next")
				if statement['directive']=='pause':
					t0 = time.perf_counter()
					delay = float(statement['statement'])
					ctx['wait'] = t0+delay
				elif statement['directive']=='send':
					if 'srv' not in statement or 'action' not in statement:
						#on ne comprend pass
						Log.send(ctx['statements'][ctx['pos']], level=3, direction="error")
						ctx['pos'] += 1
					else:
						#on demande l'execution au service
						self.ask_action(statement['srv'], statement['action'], statement['params'])
						ctx['pos'] += 1
				elif statement['directive']=='wait':
					if 'srv' not in statement or 'action' not in statement:
						#on ne comprend pass
						Log.send(ctx['statements'][ctx['pos']], level=3, direction="error")
						ctx['pos'] += 1
					else:
						#on demande l'execution au service
						ctx['wait'] = statement
						self.waitfor(self.ask_action(statement['srv'], statement['action'], statement['params']), callback=self.answer_statement, pback=ctx)
		
		if ctx['statements'] and ctx['pos'] >= len(ctx['statements']):
			Log.send("EXECUTION OVER", level=2, direction="PROC")
			self.encours = None
			#on prend la prochaine
			if self.proc2exec:
				self.prepare_proc(self.proc2exec.pop(0))
				
			
	def analyse_statement(self, statement):
		if len(statement)==0 or statement[0]=='#':
			return None
		else:
			posdirective = statement.find(":")
			if posdirective>-1:
				directive = statement[:posdirective].lower()
				statement = statement[posdirective+1:]
			
				posparam = statement.find("(")
				posfinparam = statement.rfind(")")			
				if posparam>-1 and posfinparam>-1:
					params = statement[posparam+1:posfinparam]
					ignore = statement[posfinparam+1:]
					if len(ignore)!=0:
						print("statement", statement,"| ignore=[{}]".format(ignore))
					statement = statement[:posparam]
					decoup = statement.split('.')
					if len(decoup) > 1:
						return {'directive':directive, 'statement':statement, 'srv':decoup[0], 'action':".".join(decoup[1:]), 'params':params.split(',\s*')}
					else:
						return {'directive':directive, 'statement':statement, 'params':params.split(',\s*')}
				else:
					return {'directive':directive, 'statement':statement}
		
	def answer_statement(self, rep, ctx, *karg):
		print("Reçu", karg)
		if 'wait' in ctx:
			del ctx['wait']
			ctx['pos'] += 1
		#self.execnextstatement()

	def do_service_process(self):
		super().do_service_process()
		if self.encours is not None:
			self.execnextstatement()
			


		
if __name__ == '__main__':
		
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
	test = ProcExec(name, HOST, PORT)

	keypress = kb_func()		
	while keypress != 'q':			
		## les commandes claviers
		if keypress and keypress == 'a':
			print(test.connect_central.isconnected())
		elif keypress and keypress == 'z':
			test.reconnect()
		elif keypress and keypress == 'e':
			#on change les variables
			test.action_execproc('proc_test.txt')
			
			
		keypress = kb_func()	

		#les echanges socket
		test.do_service_process()
					
		time.sleep(0.01)
		