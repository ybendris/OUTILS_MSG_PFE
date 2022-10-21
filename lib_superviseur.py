# -*- coding: utf-8 -*-
"""
Created on Wed Jun 14 15:28:18 2017

@author: cds
"""

from lib_netitem import NetworkItem
from lib_srvitem import SrvData

class Superviseur(NetworkItem, SrvData):
    def __init__(self, name, hote, port, params=[]):
        NetworkItem.__init__(self, name, hote, port, params)
		SrvData(self, params)
        self.etat = "stopped"
        self.mode = "standard"
        self.intern = "standard"
        self.spv_record()

    def spv_record(self):
        self.record_action('spv_get_etat', 'short', self.cmd_get_etat)
        self.record_action('spv_get_interne', 'short', self.cmd_get_intern)
        self.record_action('spv_get_mode', 'short', self.cmd_get_mode)
        self.record_action('spv_shutdown', 'long', self.cmd_shutdown)
        self.record_action('spv_start_supervision', 'long', self.cmd_start_supervision)
        self.record_action('spv_stop_supervision', 'long', self.cmd_stop_supervision)
        self.record_action('spv_start_measurement', 'long', self.cmd_start_measurement)
        self.record_action('spv_stop_measurement', 'long', self.cmd_stop_measurement)
        self.record_action('spv_start_recording', 'long', self.cmd_start_recording)
        self.record_action('spv_stop_recording', 'long', self.cmd_stop_recording)
        self.record_action('spv_configure', 'long', self.cmd_configure)
        self.record_action('spv_load_config', 'long', self.cmd_loadconfig)
        

    def cmd_get_etat(self, cmd):
        return self.etat
        
    def cmd_get_intern(self, cmd):
        return self.intern
        
    def cmd_get_mode(self, cmd):
        return self.mode
        
    def verif_etat(self, requis):
        """
        renvoi True si l'etat est l'un des etats requis, passe en param
        requis peut etre un string ou une liste de string
        """
        if isinstance(requis, str) and self.etat == requis:
            return True
        elif isinstance(requis, list) and self.etat in requis:
            return True
        else:
            return False            
        
    def __change_etat(self, requis, nouveau):
        if self.verif_etat(requis):
            self.etat = nouveau
            return True
        else:                    
            return False
        
    def cmd_shutdown(self, cmd):
        self.etat = "shutdown"
        return True
            
    def cmd_start_supervision(self, cmd):
        #a surcharger au besoin
        return self.__change_etat('stopped', 'idle')

    def cmd_stop_supervision(self, cmd):
        #a surcharger au besoin
        return self.__change_etat(['idle', 'error'], 'stopped')
            
    def cmd_start_measurement(self, cmd):
        #a surcharger au besoin
        return self.__change_etat('idle', 'measurement')
        
    def cmd_stop_measurement(self, cmd):
        #a surcharger au besoin
        return self.__change_etat(['measurement','recording'], 'idle')
        
    def cmd_start_recording(self, cmd):
        #a surcharger au besoin
        return self.__change_etat('measurement', 'recording')
        
    def cmd_stop_recording(self, cmd):
        #a surcharger au besoin
        return self.__change_etat('recording', 'measurement')

    def cmd_configure(self, cmd, param):
        print("configure", cmd, param)

    def cmd_loadconfig(self, cmd, param):        
        retour = self.load_param(param)
        self.dump_param()
        return retour
        