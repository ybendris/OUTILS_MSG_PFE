# -*- coding: utf-8 -*-
"""
Created on Tue Jun 13 14:44:47 2017

@author: cds
"""

import sys
import getopt
import msvcrt

from lib_service import Customer



def kb_func():
	if msvcrt.kbhit():
		try:
			ret = msvcrt.getch().decode()
			return ret
		except:
			pass
	
liste_services = None
		
def affiche_rep(arg1, arg2, arg3 = None):
	if arg2 == 'srv_list' and arg3 is None:
		global liste_services
		liste_services = arg1
	print("A la question ===========", arg2)
	print("recu		 ===============", str(arg1))
	
		
def main():	   
	try:
		opts, args = getopt.getopt(sys.argv[1:], "p:s:")
	except getopt.GetoptError:
		print('error') 
		sys.exit()
	
	service_name = "appli" 
			
	for o, a in opts:
		if o == '-p':
			server_adress = int(a)
		elif o == '-s':
			service_name = a
	
	appli = Customer('appli')
	appli.connect('localhost', 10000)
	
	   
	destinataire = None
	keypress = kb_func()	
	while keypress != 'q':
		appli.manage_messages()
					
		if keypress is not None and keypress !='q':
			print(">>{}<<".format(keypress))
			## branchement sur le superviseur qui va bien
			if keypress == '0':
				appli.send_req('central', 'bus_list', affiche_rep)
			if keypress == '1':
				destinataire = "stub"
			elif keypress == '2':
				destinataire = "hlta"
			elif keypress == 'l':
				print(destinataire)
				appli.send_req(destinataire, 'srv_list', affiche_rep)
			elif keypress == 's':
				appli.send_req(destinataire, 'shutdown', affiche_rep)
			elif keypress == 'w':
				appli.send_req(destinataire, 'start_supervision', affiche_rep)
			elif keypress == 'e':
				appli.send_req(destinataire, 'stop_supervision', affiche_rep)				
			elif keypress == 'r':
				appli.send_req(destinataire, 'start_measurement', affiche_rep)
			elif keypress == 't':
				appli.send_req(destinataire, 'stop_measurement', affiche_rep)				
			elif keypress == 'a':
				appli.send_req(destinataire, 'toto', affiche_rep, '????')
			elif keypress == 'z':
				appli.send_req(destinataire, 'get_etat', affiche_rep)
			elif keypress == 'x':
				appli.send_req(destinataire, 'get_mode', affiche_rep)
			elif keypress == 'c':
				appli.send_req(destinataire, 'get_interne', affiche_rep)
			elif keypress == 'v':
				appli.send_req(destinataire, 'get_version', affiche_rep)				   
			elif keypress == 'b':
				appli.send_req(destinataire, 'get_memory_status', affiche_rep)
			elif keypress == 'p':
				appli.send_req(destinataire, 'extra_measure', affiche_rep)
			elif keypress == 'f':
				appli.send_req(destinataire, 'load_config', affiche_rep, "c:/temp/test.txt")
			   
		keypress = kb_func()   
		
	appli.disconnect()
	
if __name__ == '__main__':
	main()
	
