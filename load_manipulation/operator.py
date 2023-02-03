"""
Operation module of HEyDU includes target function and possible actions for load manipulation

TODO:
    - sub_p_t()/ cap_comp_time()
        - duration longer then cycle (max: len(cycle.index))
        - no compensation (compensation directly after)
    - calc_curtailment()
        - calculate individual results for every load: Curtailment reduction resulting of individual load manipulation

@author: Paul Bohn
"""

__version__ = "0.1"
__author__ = "Paul Bohn"

import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


class Operator:
    """
    Class to control and manipulate environment
    """

    def __init__(self, env, target_func=None):
        """
        env: object (class Environment)
            Object contains all loads from class Equipment
        target_func: pd.DataFrame
            Target Function
        """
        self.env = env
        self.target_func = target_func
        # Functions
        self.create_tf()

    def create_tf(self):
        """
        Function to create required columns in target function
        Status:
            0: No PV production limit 0.1 kW
            1: Complete consumption of PV production
            2: Partial consumption of PV production (Curtailment)
        """
        tf = self.target_func
        tf['PV [kW]'] = np.where(tf['PV [kW]'] < 0, 0, tf['PV [kW]'])
        tf['PV after Curtailment [kW]'] = tf['PV [kW]'] - tf['Ref. Curtailment [kW]']
        tf['Ref. Curtailment [kW]'] = np.where(tf['Ref. Curtailment [kW]'] < 0, 0, tf['Ref. Curtailment [kW]'])
        tf['Curtailment [kW]'] = tf['Ref. Curtailment [kW]']
        tf['Ref. Load [kW]'] = self.env.load_ref['Reference Load']
        tf['Load [kW]'] = self.env.load_df['Total']
        tf['Manipulated'] = False
        tf['Status'] = np.where(tf['PV [kW]'] < 0.1, 0, np.where(tf['Ref. Curtailment [kW]'] <= 0, 1, 2))
        self.target_func = tf

        return self.target_func

    def total_load(self):
        """
        Function to run load_manipulation() for all equipment
        TODO:
            - Add price and CO2 factor - depending on grid or diesel system (Blackout hours needed)
        """
        optimized_curtailment = []
        total = []
        for i in range(len(self.env.variable_load)):
            self.load_manipulation(i, False)
            savings = self.calc_curtailment()
            ref_curtailment = savings[0]
            optimized_curtailment.append(savings[1])
            if i == 0:
                total.append(ref_curtailment-optimized_curtailment[i])
            else:
                total.append(optimized_curtailment[i-1]-optimized_curtailment[i])
        print('\n' + 'Total Curtailment Reduction:')
        self.calc_curtailment()
        self.create_line_chart()
        self.create_pie_chart(ref_curtailment, total)

    def load_manipulation(self, index, x=True):
        """
        Function to manipulate loads.

        index: int
            index in list
        clock: dt.datetime
            time from operator to manipulate
        """
        print('Manipulating: ' + self.env.variable_load[index].name)
        if self.env.variable_load[index].manipulation_type is None:
            print('Fixed Load - load manipulation not possible.')
            pass
        else:
            load = self.env.variable_load[index]
            for i in range(len(self.target_func.index)):
                clock = self.target_func.index[i]
                # Skip time steps with PV curtailment
                if self.target_func.loc[clock, 'Status'] == 2:
                    continue
                else:
                    # Skip manipulated time steps
                    if load.df.loc[clock, 'Controllable']:
                        if load.df.loc[load.df.index[i], 'Status'] == 2:
                            # Check load manipulation_type/run functions
                            if load.manipulation_type == 'Cap':
                                self.sub_p_t(index, clock)
                            elif load.manipulation_type == 'Shift':
                                self.sub_t(index, clock)
                            else:
                                pass
                        else:
                            pass
            self.env.summarize_load()
            self.env.update_load(index)
            self.update_target_func(index)
            if x is False:
                pass
            else:
                self.calc_curtailment()
                self.create_line_chart(index)

    def sub_t(self, index, clock):
        """
        Sub function to manipulate time of load (run by load_manipulation())

        index: int
            passed from function load_manipulation()
        clock: dt.datetime
            passed from function load_manipulation()
        """
        load = self.env.variable_load[index]
        parameters = self.shift_comp_time(clock, dt.timedelta(minutes=len(load.cycle.index)), load.period, index)
        comp_time = parameters[0]
        if comp_time is None:
            pass
            # print('Load compensation not possible within period. No reduction of PV curtailment.')
        elif not comp_time:
            print('Load already at optimal time for curtailment reduction. Timestamp: ' + str(clock) + '.')
        else:
            # Call function from load object (type: class Equipment)
            self.env.variable_load[index].shift(clock, comp_time)
            # Print Load Shifting parameters
            print(str(clock) + ': ' + str(self.env.variable_load[index].name) + ' shifted to ' +
                  str(clock + comp_time) + '.')

    def sub_p_t(self, index, clock):
        """
        Sub function to manipulate time and power of load (run by load_manipulation())

        index: int
            passed from function load_manipulation()
        clock: dt.datetime
            passed from function load_manipulation()
        TODO:
            - Compensation directly after cycle --> e.g. AC needs to cool room if compensation later room will be to hot
            - Maybe new function for compensation
        """
        load = self.env.variable_load[index]
        parameters = self.cap_comp_time(clock, dt.timedelta(minutes=len(load.cycle.index)), index, load.cap_factor)
        comp_time = parameters[0]
        duration = parameters[1]
        if comp_time is None:
            pass
            # print(str(clock) + ': Load compensation not possible within period. No reduction of PV curtailment.')
        elif not comp_time:
            pass
            # print(str(clock) + ': Load already at optimal time for curtailment reduction.')
        else:
            # Call function from load object (type: class Equipment)
            self.env.variable_load[index].cap(clock, comp_time, duration, load.cap_factor)
            # Print Load Capping parameters
            print(str(clock) + ': ' + str(self.env.variable_load[index].name) + ' capped to ' + str(
                load.cap_factor * 100) + '% for ' + str(comp_time) + ' min.')

    def shift_comp_time(self, clock, duration, period, index):
        """
        Function to find optimal compensation time for load manipulation based on maximum reduction of PV Curtailment.

        index: int
            index in env.variable_load
        clock: dt.datetime
            Manipulation start
        duration: dt.timedelta
            Manipulation duration (len(cycle.index))
        period: dt.timedelta
            Maximum time span for load compensation
        """
        tf = self.target_func
        load = self.env.variable_load[index]
        c_pv = []
        c_load = []
        c_curtailment = []
        i_period = int(period / dt.timedelta(minutes=1))
        for i in range(len(load.cycle.index)):
            t = clock + dt.timedelta(minutes=i)
            c_pv.append(tf.loc[t, 'PV [kW]']/60)
            c_load.append((self.env.load_df.loc[t, 'Total'] - load.df.loc[t, 'P_out'])/60)
            if c_pv[-1] - c_load[-1] < 0:
                c_curtailment.append(0)
            else:
                c_curtailment.append(c_pv[-1] - c_load[-1])
        f_curtailment = []
        for i in range(i_period):
            """
            Find ideal time for load compensation
            """
            start = clock + dt.timedelta(minutes=i)
            stop = clock + duration + dt.timedelta(minutes=i)
            f_curtailment.append(tf.loc[start:stop, 'Curtailment [kW]'].sum()/60)
        if all(v <= 0 for v in f_curtailment):
            comp_time = None
        elif sum(c_curtailment) >= max(f_curtailment):
            comp_time = False
        else:
            comp_time = dt.timedelta(minutes=f_curtailment.index(max(f_curtailment)))
        return comp_time, duration

    def cap_comp_time(self, clock, duration, index, factor):
        """
        Function to find optimal compensation time for load manipulation based on maximum reduction of PV Curtailment.

        index: int
            index in env.variable_load
        clock: dt.datetime
            Manipulation start
        duration: dt.timedelta
            Manipulation duration (len(cycle.index))
        period: dt.timedelta
            Maximum time span for load compensation
        """
        tf = self.target_func
        load = self.env.variable_load[index]
        # Calculate current curtailment
        c_pv = []
        c_load = []
        c_curtailment = []
        for i in range(len(load.cycle.index)):
            t = clock + dt.timedelta(minutes=i)
            c_pv.append(tf.loc[t, 'PV [kW]']/60)
            c_load.append((self.env.load_df.loc[t, 'Total'] - load.df.loc[t, 'P_out'])/60)
            if c_pv[-1] - c_load[-1] < 0:
                c_curtailment.append(0.0)
            else:
                c_curtailment.append(c_pv[-1] - c_load[-1])
        # Calculate future curtailment
        f_curtailment = []
        cycle_sum = sum(load.cycle['P_cyc [kW]'])
        cycle_average = load.cycle['P_cyc [kW]'].mean()
        delta = cycle_sum * (1-factor)
        # time = math.ceil(delta / cycle_average)
        # Compare current and future curtailment
        if all(v <= 0 for v in f_curtailment):
            comp_time = None
        elif sum(c_curtailment) >= max(f_curtailment):
            comp_time = False
        else:
            comp_time = dt.timedelta(minutes=f_curtailment.index(max(f_curtailment)))
        return comp_time, duration

    def update_target_func(self, index):
        """
        Function to update Curtailment in target function
        """
        tf = self.target_func
        load = self.env.variable_load[index].df
        tf['Load [kW]'] = self.env.load_df['Total']
        tf['Curtailment [kW]'] = np.where(tf['Curtailment [kW]'] - load['P_out'] + load['P_in'] < 0, 0,
                                          tf['Curtailment [kW]'] - load['P_out'] + load['P_in'])
        tf['Curtailment [kW]'] = np.where(tf['Status'] < 2, 0, tf['Curtailment [kW]'])

        return self.target_func, self.env.load_df

    def calc_curtailment(self):
        """
        Function to calculate curtailment reduction
        """
        ref = self.target_func['Ref. Curtailment [kW]'].sum() / 60
        opt = self.target_func['Curtailment [kW]'].sum() / 60
        print('Reference Curtailment: ' + str(round(ref, 2)) + ' kWh')
        print('Optimized Curtailment: ' + str(round(opt, 2)) + ' kWh')
        print('Curtailment Reduction: ' + str(round(ref - opt, 2)) + ' kWh')
        print('Relative Curtailment Reduction: ' + str(round((ref-opt)/ref*100, 2)) + '%')

        return ref, opt

    def create_line_chart(self, index=None):
        """
        Function to compare and plot results (load & curtailment)
        """
        tf = self.target_func
        plt.figure()
        source = ['PV [kW]', 'Ref. Curtailment [kW]', 'Curtailment [kW]', 'Ref. Load [kW]', 'Load [kW]']
        color = ['orangered', 'darkblue', 'cornflowerblue', 'darkgreen', 'lightgreen']
        label = ['PV Production', 'Reference Curtailment', 'Reference Load', 'Optimized Curtailment',
                 'Optimized Load']
        for i in range(len(source)):
            plt.plot(tf.index.to_pydatetime(), tf[source[i]], color[i], linewidth=0.8, label=label[i])
        if index is None:
            pass
        else:
            load_df = self.env.variable_load[index].df
            load_source = ['P_in', 'P_out']
            load_color = ['black', 'grey']
            load_label = [': Reference', ': Manipulated']
            for i in range(len(load_source)):
                plt.plot(tf.index.to_pydatetime(), load_df[load_source[i]], load_color[i], linewidth=0.8,
                         label=self.env.variable_load[index].name + load_label[i])
        # Format axis
        plt.gcf().autofmt_xdate()
        x_axis = mdates.DateFormatter('%H:%M')
        plt.gca().xaxis.set_major_formatter(x_axis)
        plt.title('Hospital Energy Design Utility')
        plt.ylabel('P [kW]')
        plt.xlabel('Time [hh:mm]')
        plt.tight_layout()
        plt.legend(loc=2, prop={'size': 6})
        plt.show()

    def create_pie_chart(self, ref_curtailment, reduction):
        """
        Function to create pie chart to compare curtailment reduction

        ref_curtailment: float
            Reference Curtailment
        reduction: list
            list of curtailment reduction of devices
        """
        labels = []
        values = reduction
        for i in range(len(self.env.variable_load)):
            labels.append(self.env.variable_load[i].name)
        labels.append('Optimized Curtailment')
        values.append(ref_curtailment - sum(values))
        # Create Pie Chart
        fig1, ax1 = plt.subplots()
        ax1.pie(values, labels=labels)
        ax1.axis('equal')
        plt.show()

    def calc_savings(self, reference, optimized, blackout):
        """
        Function to calculate CO2 and cost savings
        """
        # Calculation Factors
        co2_diesel = 0.81
        co2_grid = 0.28
        cost_diesel = 3.62
        cost_grid = 0.24
        reduction = reference - optimized
        if blackout is True:
            co2_savings = co2_diesel * reduction
            cost_savings = cost_diesel * reduction
        else:
            co2_savings = co2_grid * reduction
            cost_savings = cost_grid * reduction

        return co2_savings, cost_savings