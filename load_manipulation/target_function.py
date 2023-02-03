"""
Module to implement target function

@author: Paul Bohn
"""

__version__ = "0.1"
__author__ = "Paul Bohn"

import os
import pandas as pd

# Set directory
root = os.path.dirname(os.path.abspath(''))
func = '/data/target_function/target_function.csv'
directory = root + func


# Import CSV Data
target_function = pd.read_csv(directory, header=0, sep=';', index_col=0, decimal=',')
target_function.index = pd.to_datetime(target_function.index)

