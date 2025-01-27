import math
from pulp import PULP_CBC_CMD, LpProblem, LpMinimize, LpVariable, lpSum

class UntitledScheduler():
    solver = PULP_CBC_CMD(msg=True)
    
    @staticmethod
    def minimise_core(system):
        prob = LpProblem("Minimise_Cores", LpMinimize)
        taskPeriods = [task['period'] for task in system['EntityStore']]
        task_instances = [instance for instance in system['EntityInstancesStore']]
        tasks = [task for task in system['EntityStore']]
        cores = [core for core in system['CoreStore']]
        #devices = [device['name', device['wcdt']] for device in system['DeviceStore']]
        #networkDelays = [(networkDelay['name'], networkDelay['wcdt']) for networkDelay in system['NetworkDelayStore']]
        hyperPeriod = math.lcm(*taskPeriods)
        # makespan = system['PluginParameters']['Makespan']
        # schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod

        for i, core in enumerate(cores):
            core['id'] = i

        # Variables
        # Define a variable for each task instance, and core.
        a = LpVariable.dicts("a",
                            ((instance['name'], value['instance'], core['name'])
                            for instance in task_instances for value in instance['value']
                            for core in cores),
                            cat='Binary')

        b = LpVariable.dicts("b", 
                        ((instance['name'], value['instance']) 
                        for instance in task_instances for value in instance['value']),
                        lowBound=0, cat='Continuous')
        c = LpVariable.dicts("c", 
                            ((instance['name'], value['instance']) 
                            for instance in task_instances for value in instance['value']),
                            lowBound=0, cat='Continuous')
        
        # Constraint
        # 1. A task instance can have exactly one core assigned to it.
        for instance in task_instances:
            for value in instance['value']:
                prob += lpSum(a[(instance['name'], value['instance'], core['name'])] for core in cores) == 1

        # 2. All task instances under one task should have the same core assigned to it.
        for instance in task_instances:
            for i in range(len(instance['value']) - 1):
                prob += lpSum(a[(instance['name'], instance['value'][i]['instance'], core['name'])] * core['id'] 
                              for core in cores) == lpSum(a[(instance['name'], instance['value'][i + 1]['instance'], core['name'])] * core['id'] 
                                                          for core in cores)
                
        # 3. A task's execution start time must be less than or equal to execution end time.
        for instance in task_instances:
            for value in instance['value']:
                prob += b[(instance['name'], value['instance'])] <= c[(instance['name'], value['instance'])]

        # 4. A task' total execution time must be equal to the specified execution time.
        for instance in task_instances:
            for value in instance['value']:
                prob += c[(instance['name'], value['instance'])] - b[(instance['name'], value['instance'])] == value['executionTime']

        # 5.1 A task's execution start time must be greater than or equal to its LET start time, 
        # 5.2 A task's execution end time must be less than or equal to its LET end time.
        for instance in task_instances:
            for value in instance['value']:
                prob += b[(instance['name'], value['instance'])] >= value['letStartTime']
                prob += c[(instance['name'], value['instance'])] <= value['letEndTime']

        # 6. Execution intervals for the tasks instances on the same core should not have any overlaps.
        
        # Objective
        objective = lpSum(a[(instance['name'], value['instance'], core['name'])]
                            for instance in task_instances for value in instance['value']
                            for core in cores)
        prob += objective, "Minimise Core Usage"

        print(prob)
        # prob.solve()

        # for instance in task_instances:
        #     for value in instance['value']:
        #         for core in cores:
        #             if a[(instance['name'], value['instance'], core['name'])].varValue == 1:
        #                 print(f"{instance['name']}_{value['instance']} is asigned to Core {core['name']}")
        #                 start_time = b[(instance['name'], value['instance'])].varValue
        #                 end_time = c[(instance['name'], value['instance'])].varValue
        #                 print(f"{instance['name']}_{value['instance']} is assigned to Core {core['name']}, "
        #                     f"Start Time: {start_time}, End Time: {end_time}")



        # # 2. There should be enough execution time per hyper-period for each task
        # for core in cores:
        #     prob += lpSum(a[(task['name'], core['name'])] * (hyperPeriod / task['period']) * task['wcet']
        #         for task in tasks) <= hyperPeriod
            
        # for core in cores:
        #     for task1 in tasks:
        #         for task2 in tasks:
        #             if task1 != task2:
        #                 print(task1['name'], task2['name'])
        
        # # Objective
        # objective = lpSum(a[(task['name'], core['name'])] for task in tasks for core in cores)
        # prob += objective, "Minimise Core Assignment"

        # prob.solve()

        # for task in tasks:
        #     for core in cores:
        #         if a[(task['name'], core['name'])].varValue == 1:
        #             print(f"Task {task['name']} is assigned to Core {core['name']}")
        #             for instance in taskInstances:
        #                 if instance['name'] == task['name']:
        #                     instance['currentCore'] = core['name']                      
        
        # # # Variable
        # # # Variable for each task instance
        # # b = {}
        # # for instance in taskInstances:
        # #     b[instance['name']] = {}
        # #     for value in instance['value']:
        # #         b[instance['name']][value['instance']] = {
        # #             'start': LpVariable(f"{instance['name']}-{value['instance']}_start", lowBound=0, cat='Continuous'),
        # #             'end': LpVariable(f"{instance['name']}-{value['instance']}_end", lowBound=0, cat='Continuous')
        # #         }
        # #         executionTime = value['executionTime']
                
        # #         # Constraint
        # #         # 3. Execution start time must be less than or equal to execution end time.
        # #         prob += LpConstraint(name=f"{instance['name']}-{value['instance']}_start_lt_end",
        # #                     e=b[instance['name']][value['instance']]['start'] <= b[instance['name']][value['instance']]['end'])
                
        # #         # 4. Execution end time - execution start time must be equal to total execution time of the instance.
        # #         prob += LpConstraint(
        # #                     name=f"{instance['name']}-{value['instance']}_duration",
        # #                     e=b[instance['name']][value['instance']]['end'] - b[instance['name']][value['instance']]['start'] 
        # #                     == executionTime)
                
        # #         # 5. Execution time must must be within the let start time and end time.
        # #         prob += LpConstraint(e=b[instance['name']][value['instance']]['start'] >= value['letStartTime'])
        # #         prob += LpConstraint(e=b[instance['name']][value['instance']]['end'] <= value['letEndTime'])
        
        # # Assign tasks to cores
        # core_assignments = {}
        # for task in tasks:
        #     for core in cores:
        #         if a[(task['name'], core['name'])].varValue == 1:
        #             core_assignments[task['name']] = core['name']
        #             for instance in taskInstances:
        #                 if instance['name'] == task['name']:
        #                     instance['currentCore'] = core['name']

        # # Schedule task instances on assigned cores
        # for core in cores:
        #     core_tasks = [task for task in tasks if core_assignments.get(task['name']) == core['name']]
        #     core_instances = [instance for instance in taskInstances 
        #                       if instance['name'] in [task['name'] for task in core_tasks]]

        #     # Sort instances by start time (ascending)
        #     core_instances.sort(key=lambda x: x['value'][0]['letStartTime']) 

        #     # Schedule instances on the core without overlap
        #     current_time = 0
        #     for instance in core_instances:
        #         instance['value'][0]['start_time'] = current_time
        #         instance['value'][0]['end_time'] = current_time + instance['value'][0]['executionTime']
        #         current_time = instance['value'][0]['end_time']