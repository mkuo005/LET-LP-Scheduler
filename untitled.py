import math
import pandas as pd
import pulp
from pulp import PULP_CBC_CMD, LpProblem, LpMinimize, LpVariable, lpSum

class UntitledScheduler():
    solver = PULP_CBC_CMD(msg=True)
    
    @staticmethod
    def minimise_core(system):
        prob = LpProblem("Minimise_Cores", LpMinimize)
        # taskPeriods = [task['period'] for task in system['EntityStore']]
        tasks = [task for task in system['EntityStore']]
        cores = [core for core in system['CoreStore']]
        #devices = [device['name', device['wcdt']] for device in system['DeviceStore']]
        #networkDelays = [(networkDelay['name'], networkDelay['wcdt']) for networkDelay in system['NetworkDelayStore']]
        # hyperPeriod = math.lcm(*taskPeriods)
        # makespan = system['PluginParameters']['Makespan']
        # schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod

        # Variables
        # Define a variable for each task, and core.
        a = LpVariable.dicts("a",
                            ((task['name'], core['name'])
                            for task in tasks
                            for core in cores),
                            cat='Binary')
        
        # Constraint
        for task in tasks:
            prob += lpSum(a[(task['name'], core['name'])] for core in cores) == 1
        
        # Objective
        objective = lpSum(a[(task['name'], core['name'])] for task in tasks for core in cores)
        prob += objective, "Minimise Core Assignment"

        prob.solve()

        for task in tasks:
            for core in cores:
                if a[(task['name'], core['name'])].varValue == 1:
                    print(f"Task {task['name']} is assigned to Core {core['name']}")
