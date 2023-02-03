"""Tool for creating the loadprofiles"""

#TODO: create new csv with headlines,

from pathlib import Path
import pandas as pd
import numpy as np
import datetime as dt
from glob import glob

"""
@autor: Paul Bohn, Moritz End
"""



filenames_profiles = glob('C:/Users/moend/sciebo/2020_Masterprojekt_Bohn_End/HEyDU/Loadprofiles_Fraunhofer_Umsicht/lp_*.csv')
data_profiles = [pd.read_csv(f, header=0, sep=';', index_col=0,
                          converters={1: lambda x: float(x.replace('.', '').replace(',', '.'))})
              for f in filenames_profiles]

filenames_cycles = glob('C:/Users/moend/sciebo/2020_Masterprojekt_Bohn_End/HEyDU/Loadprofiles_Fraunhofer_Umsicht/cycles/lp_*.csv')
data_cycles = [pd.read_csv(f, header=0, sep=';', index_col=0,
                          converters={1: lambda x: float(x.replace('.', '').replace(',', '.'))})
              for f in filenames_cycles]

nominal_load = []
standby = []
baseload = []


def norm_profile(index):
    nominal_load.append(data_profiles[index].max())
    print(nominal_load[index])
    data_profiles[index]['P_nominal'] = data_profiles[index]['P'].div(int(nominal_load[index]))
    return data_profiles[index]

def calculate_standby(index):
    standby.append(np.amin((data_profiles[index]['P_nominal']*1.1)))

def calculate_baseload(index):
    baseload.append(np.quantile(data_profiles[index]['P_nominal'], 0.2))

def status(place):
    for i in range(len(data_profiles[place].index)):
        current_status = data_profiles[place].loc[data_profiles[place].index[i], 'Status']
        current_power = data_profiles[place].loc[data_profiles[place].index[i], 'P']
        if i == 0:
            if current_power <= standby:
                current_status = 0
            elif current_power > baseload:
                current_status = 2
            else:
                current_status = 1
        else:
            if current_power > baseload \
                    and data_profiles[place].loc[data_profiles[place].index[i - 1], 'P'] > baseload:
                current_status = 3
            elif current_power > baseload \
                    and data_profiles[place].loc[data_profiles[place].index[i - 1], 'P'] <= baseload:
                current_status = 2
            elif current_power <= standby:
                current_status = 0
            else:
                current_status = 1
        data_profiles[place].loc[data_profiles[place].index[i], 'Status'] = current_status



def profile_creator(place):
        for j in range(len(data_profiles[place].index)):
            if data_profiles[place].loc[data_profiles[place].index[j], 'Status'] == 2:
                # check when device is turned on
                if len(data_profiles[place].index) - j > len(data_cycles[place].index):
                    # check if remaining length is longer than cycle
                    for i in range(len(data_cycles[place].index)):
                        if i == 0:
                            data_profiles[place].loc[data_profiles[place].index[j + i], 'Status'] = 2
                            data_profiles[place].loc[data_profiles[place].index[j + i], 'P_in'] = data_cycles[place].loc[
                                data_cycles[place].index[i], 'P_cycle']
                        else:
                            data_profiles[place].loc[data_profiles[place].index[j + i], 'Status'] = 3
                            data_profiles[place].loc[data_profiles[place].index[j + i], 'P_in'] = data_cycles[place].loc[
                                data_cycles[place].index[i], 'P_cycle']
                            # print(cycle.loc[cycle.index[i], 'P_cyc [kW]'])
                            k = j + i + 1
                    while data_profiles[place].loc[data_profiles[place].index[k], 'Status'] == 3:
                        data_profiles[place].loc[data_profiles[place].index[k], 'Status'] = 1
                        k += 1
            elif data_profiles[place].loc[data_profiles[place].index[j], 'Status'] == 1 or len(data_profiles.index) - j < len(data_cycles.index):
                data_profiles[place].loc[data_profiles[place].index[j], 'P_in'] = baseload
            data_profiles[place]['P_in'].fillna(baseload, inplace=True)


# def turned_on(self):
#         for i in range(len(data_profiles.index)):
#             if data_profiles.loc[data_profiles.index[i], 'Status'] == 2:
#                 on.append(start + dt.timedelta(minutes=i))


for i in range(len(data_profiles)):
    norm_profile(i)
    data_profiles[i]['Status'] = np.nan
    #data_profiles[i].index = pd.to_datetime(data_profiles[i]).index
    calculate_standby(i)
    calculate_baseload(i)
    status(i)
    profile_creator(i)

print(baseload)
print(standby)
print(data_profiles)
