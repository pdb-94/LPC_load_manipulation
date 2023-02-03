"""
Main module to run Hospital Energy Design Utility (HEyDU)

@author: Paul Bohn, Moritz End
"""

__version__ = "0.1"
__author__ = "Paul Bohn, Moritz End"

import load_manipulation.operator as op
import load_manipulation.environment as env
import load_manipulation.models as md
import load_manipulation.target_function as tf
import os
import pandas as pd
import datetime as dt

# Set directory
root = os.path.dirname(os.path.abspath(''))
profile_location = '/data/profiles/'
cycle_location = '/data/cycles/'
profile_path = str(root + profile_location)
cycles_path = str(root + cycle_location)
profile_name = ['administration_climate_device.csv', 'CT.csv', 'laundry_washing_machines.csv', 'MRI.csv', 'PET-CT.csv',
                'pump_station.csv', 'steam_generator.csv', 'theather_climate_device.csv', 'x-ray_machine.csv',
                'administration_fixed_load.csv', 'laundry_fixed_load.csv', 'theather_fixed_load.csv']
cycle_name = ['administration_climate_device_cycle.csv', 'ct_cycle.csv', 'laundry_washing-machines_cycle.csv',
              'MRI_cycle.csv', 'PET-CT_cycle.csv', 'pump_station_cycle.csv', 'steam_generator_cycle.csv',
              'Theather_climatedevice_cycle.csv', 'x-ray_machine_cycle.csv', 'administration_fixed_load_cycle.csv',
              'laundry_fixed_load_cycle.csv', 'theather_fixed_load_cycle.csv']
data = []
cycle = []

# Create DataFrames from profile, cycle data
for i in range(len(profile_name)):
    data.append(pd.read_csv(str(profile_path + profile_name[i]), header=0, sep=';', index_col=0, decimal=','))
    data[-1].index = pd.to_datetime(data[-1].index)
    cycle.append(pd.read_csv(str(cycles_path + cycle_name[i]), header=0, sep=';', index_col=0, decimal=','))
    cycle[-1].index = pd.to_datetime(cycle[-1].index)

# List containers for objects
name = ['AC Administration', 'CT', 'Washing machines', 'MRI', 'PET-CT', 'Pump station', 'Steam Generator', 'AC Theater',
        'X-Ray', 'Administration Fixed Load', 'Laundry Fixed Load', 'Operation Theater Fixed Load']
department = ['Administration', 'Radiology', 'Laundry', 'Radiology', 'Radiology', 'Utility Room', 'Utility Room',
              'Operation Theater', 'Radiology', 'Administration', 'Laundry', 'Operation Theater']
power = [5.88, 13.013, 57.8, 45.32, 17.171, 8.822, 28.447, 14.7, 1.31, 13.516, 9.6697, 66.098]
manipulation_type = ['Cap', 'Shift', 'Shift', 'Shift', 'Shift',  'Cap', 'Cap', 'Cap', 'Shift', None, None, None]
period = [30, 15, 90, 30, 30, 20, 20, 20, 30, 0, 0, 0]
for i in range(len(period)):
    period[i] = dt.timedelta(minutes=period[i])
base_load = [1.68, 3.4, 0.001, 17.3, 3.43, 0.1, 7.19, 4.2, 0.92, 13.516, 9.6697, 66.098]
factor = [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0, 0, 0]
standby = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

load = []

# Create objects from class Equipment
for i in range(len(name)):
    load.append(md.Equipment(name[i], department[i], power[i], manipulation_type[i], data[i], cycle[i], period[i],
                             base_load[i], factor[i], standby[i]))
    print('Load: "' + load[i].name + '" created.')

# Environment
environment = env.Environment(load)

# Operator
operator = op.Operator(environment, tf.target_function)
# operator.total_load()
operator.load_manipulation(1)

