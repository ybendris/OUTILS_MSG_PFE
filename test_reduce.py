import getopt
import os
import sys
import matplotlib.pyplot as plt
import time
#import csv
import numpy as np
import pandas as pd
#from scipy.signal import argrelextrema
#essai de recherche des extremes locaux =>ko
from rdp import rdp
from scipy import signal
import matplotlib
import matplotlib.pyplot as plt    


def smooth(data):
	print(len(data))
	wl = 11
	t1 = time.process_time()		
	sg = signal.savgol_filter(data, window_length=wl, polyorder=2)
	t2 = time.process_time()
	print("smooth : {}=>{} en {}s".format(len(data), len(sg), t2-t1))
	
	return sg
	
def filt(data):
	t1 = time.process_time()		
	#sos = signal.butter(10, 50, 'low', fs=1000, output='sos')
	#res = signal.sosfilt(sos, data)
	#1000 => nombre de valeurs par secondes
	#50 => frequence au dessus de la laquelle il faut filtrer
	b, a = signal.butter(4, 50/1000, 'low', analog=False)
	res = signal.filtfilt(b, a, data)
	t2 = time.process_time()
	print("filt : {}=>{} en {}s".format(len(data), len(res), t2-t1))
	
	return res

def ssech(data):
	return data[::20]

def simplifie(data, epsilon =0.5):
	#print(data)
	t1 = time.process_time()	
	r = rdp(data, epsilon)
	t2 = time.process_time()
	print("reduce : {}=>{} en {}s".format(len(data), len(r), t2-t1))
	#print(r)
	return r

if __name__ == '__main__':
	opts, args = getopt.getopt(sys.argv[1:], "p:e:")

	#les options
	dopts = dict(opts)
	
	if len(args)<1:
		print(sys.argv[0], "-p param -e epsilon source")
		print(sys.argv[0], "-p param specifie le nom du param a prendre en compte (1er par défaut)")
		print(sys.argv[0], "-e epsilon spécifie le coefficient epsilon pour l'algo Ramer-Douglas-Peucker (0,5 par défaut)")
	else:
		t1 = time.process_time()
		filename = args[0]		
		epsilon = 0.5
		if '-e' in dopts:
			epsilon = float(dopts['-e'])
			
		with open(filename,'r') as fp:
			line = fp.readline()
			lparams = line.rstrip().split("\t")
			line = fp.readline()
			lunits = line.rstrip().split("\t")

		df = pd.read_csv(filename, header=None, skiprows=2, delimiter='\t', decimal=".", names=lparams)
				
		param = list(df)[1]
		if '-p' in dopts:
			param = dopts['-p']
		
		figure = plt.figure()
		ax = figure.add_subplot(111)
		incr = 2000
		marge = 200
		dfn = pd.DataFrame({'t':[], 'par':[]})
		for sec in range(1000, 20000, incr):
			print("======")
			t = df['t'].iloc[sec-marge:sec+incr+marge].values
			val = df[param].iloc[sec-marge:sec+incr+marge].values
			#ax.plot(t, val, c='k')
			
			sm = smooth(val)
			#ax.plot(t[marge:-marge], sm[marge:-marge], c='b')
			t1 = time.process_time()	

			sm = filt(val)
			ax.plot(t[marge:-marge], sm[marge:-marge], c='r')			
			ax.plot(t[marge:-marge:10], sm[marge:-marge:10], c='y')
			
			
			args_max = signal.argrelextrema(sm[marge:-marge], np.greater, mode='wrap')[0]
			args_min = signal.argrelextrema(sm[marge:-marge], np.less, mode='wrap')[0]
			
			args_ech = range(0, incr, 40)			
			args_ext = np.sort(np.concatenate((args_min, args_max, args_ech)))
			#args_ext = np.sort(np.concatenate((args_min, args_max, args_min-1, args_max-1)))
			dfn = dfn.append(pd.DataFrame({'t':t[marge:-marge][args_ext], 'par':sm[marge:-marge][args_ext]}))
			t2 = time.process_time()	
			
			print("{}ptx vs {}ptx // {}ptx en {}s".format(len(args_ext), incr, len(t[marge:-marge:10]),t2-t1))
			ax.plot(t[marge:-marge][args_ext]+0.2, sm[marge:-marge][args_ext], c='b')
			
			
			'''
			new = np.column_stack((t, val))
			simplifie(new, 0.5)
			sm2 = np.column_stack((val, sm))
			new2 = np.column_stack((t, sm))
			res = np.swapaxes(simplifie(new2, 0.01),0,1)
			ax.plot(res[0], res[1], c='b')
			#print(sm2)
			print(res[0])
			'''
			
			
			
		plt.show()
		print(dfn)
			

		"""
		out = pd.DataFrame()
		out['t'] = df['t'].iloc[1:].values
		out[param]=df[param].iloc[1:].values
		out['t'] = out['t'].astype(float).round(3)
		out[param]=out[param].astype(float)
		
		out2 = simplifie(out, epsilon)
		
		
		
		outfile = ".".join(filename.split(".")[:-1])+'_reduced'+'.tab'
		units=lunits
		out.to_csv(outfile, sep='\t', index=False, decimal='.', header=lunits, encoding='utf-8')
		"""

		