import dateutil.parser
import json
from datetime import datetime
import sys

#avoiding hard code here so we can use this later
#user only needs to edit this portion of code
class unix_time:
    def __init__(self, filename):
        self.filename = filename
        self.year=[]
        self.day=[]
        self.hour=[]
        self.month=[]
        self.key1_year = 'Year'
        self.key4_month = 'month'
        self.key2_day = 'DOY'
        self.key3_hour = 'Hour'
        self.unix_time_update_file()

    def unix_time_update_file(self):
        'extracting data out of a json file and combining data into one list in order to convert time to unix'
        json_data = self.filename
        for item in json_data:
            try:
                if self.key1_year not in item.values():
                    self.year.append(item[self.key1_year])
            except KeyError:
                self.year.append(1976)
        for item in json_data:
            try: 
                if self.key4_month not in item.values():
                    self.month.append(item[self.key4_month])
            except KeyError:
                self.month.append(11)
        for item in json_data:
            try: 
                if self.key2_day not in item.values():
                    self.day.append(item[self.key2_day])
            except KeyError:
                self.day.append(11)
        for item in json_data:
            try:
                if self.key3_hour not in item.values():
                    self.hour.append(item[self.key3_hour])
            except KeyError:
                self.hour.append(11)

        new = self.year+self.month+self.day+self.hour
        b=[str(x) for x in new]
        b = '/'.join(b)
        #unix time
        unix = dateutil.parser.parse(b).timestamp()
        #rounding to keep off decimals
        unix = (round(unix))
        #converting file to string in order to dump to json/dict
        json_data = ''.join([str(elem) for elem in json_data]) 
        #this does what json dumps/loads would do converts to dict
        json_data = eval(json_data)
        #uploading dict
        json_data.update({'Unix_time':unix})
        print(json_data)
        #deleting unwanted data from the dict
        for func in [self.key1_year,self.key4_month,self.key2_day,self.key3_hour]:
            try: 
                del json_data[func]
            except KeyError as e:
                pass
        sys.stdout.write(json_data)
        return True
flowfile = sys.stdin.buffer.read()
wu = unix_time(flowfile)
wu()