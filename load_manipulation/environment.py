"""
Environment module of HEyDU summarizes fixed and variable loads

TODO:
    - index as time without Date (pd.to_datetime is probably the wrong way)

@author: Paul Bohn
"""

__version__ = "0.1"
__author__ = "Paul Bohn"

import pandas as pd


class Environment:
    """
    Class to display the hospital in an energetic context
    """
    def __init__(self, load):
        """
        load: list
            contains all loads
        """
        self.load = load
        # Load container
        self.all_load = []
        self.fix_load = []
        self.variable_load = []
        # DataFrames
        self.variable_df = pd.DataFrame()
        self.fix_df = pd.DataFrame()
        self.load_df = pd.DataFrame()
        self.load_ref = pd.DataFrame()
        # Functions
        self.get_load()
        self.summarize_load()
        self.ref_load()

    def get_load(self):
        """
        Categorize load
        Fix load: list
            Non manipulative
        Variable load: list
            Manipulative
        """
        priority_cap = []
        priority_cs = []
        priority_shift = []
        for i in range(len(self.load)):
            self.all_load.append(self.load[i])
            if self.load[i].manipulation_type is None:
                self.fix_load.append(self.load[i])
            elif self.load[i].manipulation_type == 'Shift':
                priority_shift.append(self.load[i])
            elif self.load[i].manipulation_type == 'Cap/Shift':
                priority_cs.append(self.load[i])
            elif self.load[i].manipulation_type == 'Cap':
                priority_cap.append(self.load[i])
        self.variable_load = priority_shift + priority_cs + priority_cap

    def ref_load(self):
        self.load_ref['Reference Load'] = self.load_df['Total']

    def summarize_load(self):
        """
        Function to create DataFrames from load
        fix_df: pd.DataFrame
            Contains fix loads
        variable_df: pd.DataFrame
            Contains variable loads
        load_df: pd.DataFrame
            Contains all loads
        """
        # Create DataFrames
        for i in range(len(self.variable_load)):
            self.variable_df[self.variable_load[i].name] = self.variable_load[i].df['P_out']
        for j in range(len(self.fix_load)):
            self.fix_df[self.fix_load[j].name] = self.fix_load[j].df['P_ref [kW]']
        # Concat fix_df & variable_df
        self.load_df = pd.concat([self.variable_df, self.fix_df], axis=1)
        # Calculate sum for each row in DataFrames
        self.variable_df['Total'] = self.variable_df.sum(axis=1)
        self.fix_df['Total'] = self.fix_df.sum(axis=1)
        self.load_df['Total'] = self.load_df.sum(axis=1)

        return self.variable_df, self.fix_df, self.load_df

    def update_load(self, index):
        """
        Function to update summarized loads after manipulation
        index: int
            Position in self.variable_load
        """
        # Remove column Total
        variable_col = list(self.variable_df)
        variable_col.remove('Total')
        fix_col = list(self.fix_df)
        fix_col.remove('Total')
        # Add column for manipulated device
        self.variable_df[self.variable_load[index].name] = self.variable_load[index].df['P_out']
        # Calculate sum for each row in variable_df
        self.variable_df['Total'] = self.variable_df[variable_col].sum(axis=1)
        # Calculate sum for each row in load_df
        self.load_df = pd.concat([self.variable_df[variable_col], self.fix_df[fix_col]], axis=1)
        self.load_df['Total'] = self.load_df.sum(axis=1)

        return self.variable_df, self.fix_df, self.load_df
