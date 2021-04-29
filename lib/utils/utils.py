###################################
###     All utils functions     ###
###################################

import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta

def human_format(num):
    # have to do times 1000 because we are looking at kWh and not Wh
    num = num*1000
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    # add more suffixes if you need them
    return '%.2f%s' % (num, [' Wh', ' kWh', ' mWh', ' gWh', ' tWh', ' pWh'][magnitude])

def read_data(location):

    data = pd.read_pickle(location)

    # Functie voor het achterhalen van dagen en week info
    all_days = [x.split(' ')[0] for x in data["Date"]]
    unique_days = dict.fromkeys(all_days)

    i = 0
    for k in unique_days:
        unique_days[k] = 1+i
        i += 1
        
    data["dag"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%d %B %Y") for x in data["Date"]]

    data["soort_dag"] = ["Werkdag" if datetime.strptime(x, '%Y-%m-%d %H:%M:%S').weekday() < 5 else "Weekend" for x in data["Date"]]

    data["Week"] = [' '.join(map(str, datetime.strptime(x, '%Y-%m-%d %H:%M:%S').isocalendar()[:2])) for x in data["Date"]]
    data["Maand"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%B %Y") for x in data["Date"]]

    data = data[data["Maand"] != "March 2019"].reset_index(drop=True)
    
    return data

def correct_month(tmp, month):
    maanden = tmp["Maand"].unique()[month[0]:month[1]]
    maand_data = tmp[tmp["Maand"].isin(maanden)]

    return maand_data

def correct_week(tmp, month):
    month_data = correct_month(tmp, month)
    weken = tmp[tmp["Week"].isin(month_data["Week"].unique())]
    weken = weken.groupby(['Week','dag']).size().reset_index()  

    tmp_info = []
    tmp_keys = []
    for i in weken["Week"].unique():
        tmp = weken[weken["Week"] == i].reset_index(drop=True)
        tmp["month"] = [x.split(' ')[1] for x in tmp["dag"]]
        month_tmp = tmp["month"].unique()
        if len(month_tmp) > 1:
            min_tmp = list(tmp[tmp["month"] == month_tmp[1]]["dag"])[0]
            max_tmp = list(tmp[tmp["month"] == month_tmp[0]]["dag"])[-1]
        else:
            min_tmp = tmp["dag"][0].split(" ")[0]
            max_tmp = list(tmp["dag"])[-1]
            
        tmp_info.append(f"{min_tmp} - {max_tmp}")
        tmp_keys.append(f"{i}")
        
    weken = dict(zip(tmp_keys, tmp_info))
    
    return weken

def standardized_frame(data_cache, adresses):
    combined_data = []
    for adress in adresses:
        data = data_cache[['Date', 'dag', 'soort_dag', 'Week', 'Maand', f'{adress}', f'{adress} monthly BP']]
        data = data.rename(columns={f'{adress}': "OP value", f'{adress} monthly BP': "BP montly value"})
        data["adress"] = adress

        data["OP value"] = data["OP value"] * -1 
        # Dag sum
        tmp = data.groupby(['dag'], as_index = False, sort=False).agg({'OP value': 'sum'})
        tmp = tmp.rename(columns={"OP value": "OP value daysum"})
        data = pd.merge(data, tmp, on="dag")

        #Het gemiddelde 24 uurs energieprofiel (verbruik, productie en saldo) van de werkdagen per kalendermaand;
        tmp = data[data["soort_dag"] == "Werkdag"]
        tmp2 = tmp.groupby(['Week'], as_index = False, sort=False).agg({'OP value': 'sum', "OP value daysum": 'mean'})
        tmp2 = tmp2.rename(columns={"OP value": "OP value weeksum", "OP value daysum":"OP value weekmean"})
        tmp = pd.merge(tmp, tmp2, on="Week")

        #Het gemiddelde 24 uurs energieprofiel (verbruik, productie en saldo) van de weekenden perkalendermaand;
        tmp2 = data[data["soort_dag"] == "Weekend"]
        tmp3 = tmp2.groupby(['Week'], as_index = False, sort=False).agg({'OP value': 'sum', "OP value daysum": 'mean'})
        tmp3 = tmp3.rename(columns={"OP value": "OP value weeksum", "OP value daysum":"OP value weekmean"})
        tmp2 = pd.merge(tmp2, tmp3, on="Week")

        data = pd.concat([tmp, tmp2]).sort_values(by=['Date']).reset_index(drop=True)
        combined_data.append(data)

    combined_data = pd.concat(combined_data).reset_index(drop=True)

    return(combined_data)

def summarize_data(data, month, weer):
    data = correct_month(data, month)

    #weer
    weer = weer.drop(['dag'], axis=1)
    weer = weer.groupby(['Maand'], as_index = False, sort=False).agg({'zon': 'sum'})
    data = pd.merge(data, weer, on="Maand")
    
    data = data.groupby(['Maand'], as_index = False, sort=False).agg({'OP value': 'sum', 'BP montly value': "mean", "zon":"mean"})
    saldo = float(data["OP value"].sum())
    produced = float(data["BP montly value"].sum())
    used = saldo - produced
    weer = float(data["zon"].sum())

    return [f'{human_format(int(produced))}', f'{human_format(int(used))}', f'{human_format(int(saldo))}', f'{int(weer)} Uur']
