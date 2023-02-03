"""
Models module of HEyDU contains classes and virtual actions to interact with operator

@author: Paul Bohn
"""

__version__ = "0.1"
__author__ = "Paul Bohn"

import datetime as dt


class Hospital:
    """
    Class to create hospital
    """

    def __init__(self, user, name, location, employees, patients, area, building):
        """
        user: str
            Name of user
        name: str
            Name of hospital
        location: str
            Location of hospital
        employees: int
            Number of employees working
        patients: int
            Patient capacity of hospital
        area: float
            Total area of hospital [m²]
        buildings: int
            Number of buildings
        """
        self.user = user
        self.name = name
        self.location = location
        self.area = area
        self.building = building
        self.employees = employees
        self.patients = patients
        self.department = []
        self.all_equipment = []

    def update_equipment(self):
        """
        Function to update equipment list
        """
        for i in range(len(self.department)):
            for j in range(len(self.department[i].room)):
                self.all_equipment.append(self.department[i].room[j].equipment)


class Department(object):
    """
    Class to create hospital departments
    """

    def __init__(self, name, area, employees, patients):
        """
        name: str
            Name of department
        area: float
            Area of department [m²]
        employees: int
            Number of employees working in department
        patients: int
            Patient capacity of department
        """
        self.name = name
        self.area = area
        self.employees = employees
        self.patients = patients
        self.room = []


class Room:
    """
    Class to create rooms
    """

    def __init__(self, name, area, department):
        """
        name: str
            Name of Room
        area: float
            Area of room [m²]
        department: str
            Room related department
        """
        self.name = name
        self.area = area
        self.department = department
        self.equipment = []


class Equipment:
    """
    Class to create equipment
    """

    def __init__(self, name, room, power, manipulation_type, profile, cycle, period, base_load, cap_factor=1, standby=0,
                 timestep=dt.timedelta(minutes=1)):
        """
        name: str
            name of equipment device
        room: str
            room of equipment device
        power: float
            nominal power of equipment device
        manipulation_type: str
            favored type of manipulation (Cap, Shift, Cap/Shift, None)
        profile: pd.DataFrame
            profile of reference equipment device
        cycle: pd.DataFrame
            cycle of one use
        period: dt.timedelta
            max. time for load compensation
        base_load: float
            base load of the equipment device (Status 1)
        standby: float (default 0.0)
            standby load of equipment device (status 0)
        cap_factor: float (default 1.0)
        timestep: dt.datetime (default minutes=1)
            time resolution
        """
        self.name = name
        self.room = room
        self.power = power
        self.manipulation_type = manipulation_type
        self.df = profile
        self.cycle = cycle
        self.period = period
        self.base_load = base_load
        self.standby = standby
        self.cap_factor = cap_factor
        self.timestep = timestep
        # Dataframes
        self.df['Status'] = 0
        self.df['Controllable'] = True
        # Lists
        self.on = []
        # Functions
        self.update_status('P_ref [kW]')
        self.create_profile()
        self.p_out()

    def update_status(self, column):
        """
        Function to write equipment status
        column: String
            Column name in self.df
        status:
            0: standby
            1: base load
            2: start
            3: running
        """
        if self.manipulation_type is None:
            pass
        else:
            for i in range(len(self.df.index)):
                current_status = self.df.loc[self.df.index[i], 'Status']
                current_power = self.df.loc[self.df.index[i], column]
                if i == 0:
                    if current_power <= self.standby:
                        current_status = 0
                    elif current_power > self.base_load:
                        current_status = 2
                    else:
                        current_status = 1
                else:
                    if current_power > self.base_load \
                            and self.df.loc[self.df.index[i - 1], column] > self.base_load:
                        current_status = 3
                    elif current_power > self.base_load \
                            and self.df.loc[self.df.index[i - 1], column] <= self.base_load:
                        current_status = 2
                    elif current_power <= self.standby:
                        current_status = 0
                    else:
                        current_status = 1
                self.df.loc[self.df.index[i], 'Status'] = current_status

    def create_profile(self):
        """
        Function to create load profiles from status with cycle
        """
        if self.manipulation_type is None:
            pass
        else:
            for j in range(len(self.df.index)):
                # Check when device status is ON
                if self.df.loc[self.df.index[j], 'Status'] == 2:
                    # Check if remaining length is longer than cycle
                    if len(self.df.index) - j >= len(self.cycle.index):
                        for i in range(len(self.cycle.index)):
                            if i == 0:
                                self.df.loc[self.df.index[j + i], 'Status'] = 2
                                self.df.loc[self.df.index[j + i], 'P_in'] = self.cycle.loc[
                                    self.cycle.index[i], 'P_cyc [kW]']
                            else:
                                self.df.loc[self.df.index[j + i], 'Status'] = 3
                                self.df.loc[self.df.index[j + i], 'P_in'] = self.cycle.loc[
                                    self.cycle.index[i], 'P_cyc [kW]']
                                k = j + i + 1
                    else:
                        while self.df.loc[self.df.index[k], 'Status'] == 3:
                            self.df.loc[self.df.index[k], 'Status'] = 1
                            k += 1
                elif self.df.loc[self.df.index[j], 'Status'] == 1 or len(self.df.index) - j < len(self.cycle.index):
                    self.df.loc[self.df.index[j], 'P_in'] = self.base_load
            self.df['P_in'].fillna(0, inplace=True)

    def p_out(self):
        if self.manipulation_type is not None:
            self.df['P_out'] = self.df['P_in']

    def shift(self, clock, step):
        """
        Function to shift load
        clock: dt.datetime
            time from operator
        step: dt.timedelta
            time difference for load shifting
        """
        if self.df.loc[clock, 'Status'] != 2:
            print('Load shifting not possible. Choose time when cycle starts.')
        elif not self.df.loc[clock, 'Controllable']:
            print('Load shifting not possible. Load already manipulated.')
        else:
            """Check if new cycle starts during process"""
            status_check = []
            for i in range(len(self.cycle.index)):
                if self.df.loc[clock + step + dt.timedelta(minutes=i), 'Status'] == 2:
                    status_check.append(True)
                else:
                    status_check.append(False)
            if True in status_check:
                print('Cycle starts during load shifting. Choose different parameters.')
            else:
                """Load shifting"""
                # delta = dt.timedelta(minutes=len(self.cycle.index))
                # self.df.loc[clock:clock + delta, 'P_out'] = self.base_load
                # self.df.loc[clock + step: clock + step + delta, 'P_out'] = self.df.loc[clock:clock + delta, 'P_in']
                # self.df.loc[clock + step: clock + step + delta, 'Controllable'] = False
                for j in range(len(self.cycle.index)):
                    delta_j = dt.timedelta(minutes=j)
                    self.df.loc[clock + delta_j, 'P_out'] = self.base_load
                for k in range(len(self.cycle.index)):
                    delta_k = dt.timedelta(minutes=k)
                    self.df.loc[clock + step + delta_k, 'P_out'] = self.df.loc[clock + delta_k, 'P_in']
                    self.df.loc[clock + step + delta_k, 'Controllable'] = False
        self.update_status('P_out')
        return self.df['P_out']

    def cap(self, clock, step, time, factor):
        """
        Function for load capping
        clock: dt.datetime
            time from operator
        time: integer
            time span during load is capped
        step: dt.datetime
            time difference between capping and compensation
        factor: float
            percentile for load capping
        """
        if self.df.loc[clock, 'Status'] != 2:
            print('Load shifting not possible. Choose time when cycle starts.')
        elif not self.df.loc[clock, 'Controllable']:
            print('Load shifting not possible. Load already manipulated.')
        else:
            status_check = []
            power_check = []
            i_time = int(time / self.timestep)
            for i in range(i_time):
                if self.df.loc[clock + dt.timedelta(minutes=i), 'Status'] < 2:
                    status_check.append(False)
                else:
                    status_check.append(True)
                if self.df.loc[clock + dt.timedelta(minutes=i), 'P_in'] * factor <= self.base_load:
                    power_check.append(False)
                else:
                    power_check.append(True)
            if False in status_check:
                print('Load capping not possible. Device in standby/base mode. Choose different parameters.')
            elif False in power_check:
                print('Load capping not possible. P_out < base load. Choose different factor.')
            elif not self.df.loc[clock, 'Controllable']:
                print('Load capping not possible. Load already manipulated.')
            else:
                drp = []
                for j in range(i_time):
                    delta_j = dt.timedelta(minutes=j)
                    self.df.loc[clock + delta_j, 'P_out'] = self.df.loc[clock + delta_j, 'P_in'] * factor
                    drp.append(self.df.loc[clock + delta_j, 'P_in'] - self.df.loc[clock + delta_j, 'P_out'])
                for k in range(i_time):
                    delta_k = dt.timedelta(minutes=k)
                    self.df.loc[clock + time + step + delta_k, 'P_out'] = \
                        self.df.loc[clock + time + step + delta_k, 'P_in'] + drp[k]
                    drp.append(self.df.loc[clock + time + step + delta_k, 'P_in'] - self.df.loc[
                        clock + time + step + delta_k, 'P_in'] + drp[k])
                    self.df.loc[clock + time + step + delta_k, 'Controllable'] = False
        self.update_status('P_out')
        return self.df['P_out']


'''
---------------------------------------------
'''
# create_profile()
# start = self.df.index[j]
# end = self.df.index[j+len(self.cycle.index)]
# self.df.loc[start:end, 'Status'] = 3
# self.df.loc[start:end, 'P_in'] = self.cycle.loc[self.cycle.index[0]:self.cycle.index[len(self.cycle.index)-1], 'P_cyc [kW]']
# self.df.loc[start, 'Status'] = 2
# k = j + len(self.cycle.index) + 1
