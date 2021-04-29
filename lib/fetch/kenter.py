import requests
from base64 import b64encode
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from functools import reduce

# Get a list of dates from January 2019 till now

def kenter_retrieve(location, year=2019, month=5, day=1):
    sdate = date(year,month,day)
    today = datetime.today()
    dates = pd.date_range(sdate,today-timedelta(days=0),freq='m')

    # UserAndPass
    headers = { 'Authorization' : 'Basic %s' %  userAndPass }
    response = requests.get('https://webapi.meetdata.nl/api/1/meters', headers=headers)
    data = response.json()

    adresses = ["Tufsteen 4", "Tufsteen 5", "Tufsteen 6", "Tufsteen 7", "Tufsteen 8", "Tufsteen 9"]
    meetdata = []
    for i in data:
        EAN = i["connectionId"]
        # Select BP meter:
        for j in i["meteringPoints"]:
            if j["meteringPointType"] == 'BP':
                BP = j
                
        # Select main meter by OP, as this contains timepoint information
        for j in i["meteringPoints"]:
            if j["meteringPointType"] == 'OP':
                i = j
                
        masterData = i["masterData"][0]
        #Hard adress filter <- if you want another adress to be checked please add in the addresses list
        adress = masterData["address"]
        if adress not in adresses:
            continue
            
        meterid = i["meteringPointId"]
        
        #So now loop through the information of the meter by month for every month starting at January 2019 till the month of today using dates
        adress_data = []
        for month in dates:
            #Special if statements for Tufsteen 5 and 6
            if adress == "Tufsteen 5":
                meterid = "00059423"
                month_info = requests.get(f'https://webapi.meetdata.nl/api/1/measurements/{EAN}/{meterid}/{month.year}/{month.month}', headers=headers)
                month_info = month_info.json()
                timepoints = [datetime.fromtimestamp(x["timestamp"]).strftime('%Y-%m-%d %H:%M:%S') for x in month_info["10180"]]
                datapoints_given = [float(x["value"]) for x in month_info["10180"]]
                datapoints_back = [float(x["value"]) for x in month_info["10280"]]
                datapoints = [a_i - b_i for a_i, b_i in zip(datapoints_given, datapoints_back)]
            elif adress == "Tufsteen 6":
                meterid = "00059425"
                month_info = requests.get(f'https://webapi.meetdata.nl/api/1/measurements/{EAN}/{meterid}/{month.year}/{month.month}', headers=headers)
                month_info = month_info.json()
                timepoints = [datetime.fromtimestamp(x["timestamp"]).strftime('%Y-%m-%d %H:%M:%S') for x in month_info["10180"]]
                datapoints_given = [float(x["value"]) for x in month_info["10180"]]
                datapoints_back = [float(x["value"]) for x in month_info["10280"]]
                datapoints = [a_i - b_i for a_i, b_i in zip(datapoints_given, datapoints_back)]
            else:
                month_info = requests.get(f'https://webapi.meetdata.nl/api/1/measurements/{EAN}/{meterid}/{month.year}/{month.month}', headers=headers)
                month_info = month_info.json()
                timepoints = [datetime.fromtimestamp(x["timestamp"]).strftime('%Y-%m-%d %H:%M:%S') for x in month_info["16080"]]
                datapoints = [float(x["value"]) for x in month_info["16080"]]
                
            # Get BP info
            BP_info = requests.get(f'https://webapi.meetdata.nl/api/1/measurements/{EAN}/{BP["meteringPointId"]}/{month.year}/{month.month}', headers=headers)
            BP_info = BP_info.json()
            
            if not BP_info:
                BP_info = 0
            else:
                BP_info = BP_info["18280"][0]["value"]
            
            adress_data.append(pd.DataFrame(data={'Date': timepoints, f'{adress}': datapoints, f'{adress} monthly BP': BP_info}))
            
        meetdata.append(pd.concat(adress_data))
        
    meetdata = reduce(lambda x, y: pd.merge(x, y, on = 'Date'), meetdata)

