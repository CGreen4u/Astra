import pandas as pd
import numpy as np
import torch
import torch.utils.data
import pickle
import argparse
import pdb
import numpy 
import swdata
import pdb
import os.path
from os import path
from kafka import KafkaConsumer

class kafka_consumer1:
#clear the key from list after running
    #all information comes in as bytes and must be converted
    
    def bytesToDictionary(b_array): #all data comes in as bytes
         try:
             d = dict(toks.split(":") for toks in b_array.decode("utf-8").split(",") if toks) #method for collecting data
             #print("Convert")
             return d
         except ValueError as e:
             print(e) #error for data that is not meant
    consumer = KafkaConsumer('test',consumer_timeout_ms=10000) #How long will the consumer wait after a message?
    #print(type(consumer))
    filepath = []
    key_uuid = []
    filename = []
    worker_uuid = []
    for msg in consumer: #reviewing messge, looking for specific information inorder to append
        print(msg)
        d = bytesToDictionary(msg.value)# calling bytes funciton to look though data
        s = msg.value.decode("utf-8") #decode so python can read
        if 'key_uuid' in s:
            key_uuid.append(d['key_uuid'])
        if 'filepath' in s:
            filepath.append(d['filepath'])
        if 'filename' in s:
            filename.append(d['filename'])
        if 'worker_uuid' in s:
            worker_uuid.append(d['worker_uuid'])
            break
        print(filepath)
        print(filename)
        print(key_uuid)
    filepath = ",".join(filepath) #dump location
    filename = ",".join(filename) #dump name
    key_uuid = [int(i) for i in key_uuid] # converting string into int
    worker_uuid = ",".join(worker_uuid) #converting uuid 
    consumer.close() #always close consumer
        #print(d)
kafka_consumer1() #running script


outfile = '/home/chris/Documents/Heartbeat/workingVer/exampleData5.pickle'
infile = '/home/chris/Documents/Heartbeat/workingVer/exampleData.csv'
interp_limit = 90
TSL = 4
dRes = 30
tHist = 120
pWindow = 300
popFeats = []
tnames = ['AE', 'AL', 'AU', 'DST']

def getData(infile, outfile, interp_limit, TSL, dRes, tHist, pWindow, popFeats, tnames, pre_resolution = 5):

    rawData = pd.read_csv(infile, delimiter=' ') #read raw CSV file
    fullLabels = list(rawData.keys()) # Get list of labels from the dataframe
    rawData = rawData.replace([99999.9, 9999.99, 999.99, '#REF!'], np.nan) #OMNIweb database encodes missing values this way..
    rawData.iloc[:, TSL:] = rawData.iloc[:, TSL:].interpolate(limit=int(interp_limit/pre_resolution))
    rawData = rawData.astype('float')

    for feat in popFeats: #Remove any features in popfeats
        print(feat)
        rawData.pop(feat)

    labels = list(rawData.keys())
    tcols = [labels.index(i) for i in tnames] # Get indices of the targets from tnames

    avgData = rawData
    for name in labels[TSL:]:
        avgData[name] = rawData[name].rolling(window=int(dRes/pre_resolution)).mean()

    rawLabels = avgData.iloc[:, tcols].to_numpy(copy=True)
    intRes = dRes/pre_resolution
    intLength = tHist/dRes
    nSamples = len(rawData)
    nFeats = len(labels) - TSL
    maxLen = int(intLength)

    y = np.zeros([nSamples, int(pWindow/dRes), len(tnames)])
    y[:] = np.nan
    x = np.zeros((nSamples, maxLen, nFeats + TSL))
    x[:] = np.nan
    SWV = avgData.iloc[:, TSL:].to_numpy() ## working with averaged data

    for i in range(nSamples):

        for j in range(nFeats):
            start = int((i - pWindow/pre_resolution) - tHist/pre_resolution + dRes/pre_resolution)
            stop = int(i - pWindow/pre_resolution + dRes/pre_resolution)
            step = int(intRes)

            if(start >= 0):
                    x[i, :, :TSL] = avgData.iloc[start:stop:step, :TSL].to_numpy()
                    tempD = SWV[start:stop:step, j]
                    labels = rawLabels[stop:int(i + dRes/pre_resolution):step]
                    n = np.count_nonzero(np.isnan(tempD))

                    if(int(n)==0):
                        temp = torch.zeros(maxLen)
                        temp[-len(tempD):] = torch.from_numpy(tempD.copy())
                        x[i, :, TSL + j] = temp
                        y[i, :, :] = torch.squeeze(torch.from_numpy(labels.copy()))

    df = int(dRes/pre_resolution) #decimation factor
    x = x[::df]
    y = y[::df]
    nas = np.logical_or(np.isnan(y).any(1).any(1), np.isnan(x).any(1).any(1))
    x = x[np.logical_not(nas)]
    y = y[np.logical_not(nas)]

    x = torch.Tensor(x)
    y = torch.Tensor(y)
    print(x)
    print(y)
    with open(outfile, 'wb') as f:
        pickle.dump([x, y, fullLabels], f)
        print(outfile)

if(path.exists(outfile)):
    print("I'm not running that! You'll overwrite the existing file!")
else:
    getRNNData.getData(infile, outfile, interp_limit, TSL, dRes, 
            tHist, pWindow, popFeats, tnames)
