import pickle
import numpy 
import getTimeSeriesData
import swdata
import pdb
import os.path
from os import path

outfile = 'datasets/13T15DataRANDO.pickle'
infile = 'datasets/13T15DataSDR.csv'
interp_limit = 90
TSL = 4
dRes = 30
tHist = 120
pWindow = 300
popFeats = []
tnames = ['AE', 'AL', 'AU', 'SYM/H']

if(path.exists(outfile)):
    print("I'm not running that! You'll overwrite the existing file!")
else:
    getTimeSeriesData.getData(infile, outfile, interp_limit, TSL, dRes, 
            tHist, pWindow, popFeats, tnames, series=True, decimate=True, pRes=5)

