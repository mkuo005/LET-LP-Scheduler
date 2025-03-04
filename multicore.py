import math
from pulp import PULP_CBC_CMD, LpProblem, LpMinimize, LpVariable, lpSum

from min_core_usage import MinCoreUsage
from min_e2e_mc import MinE2EMC

class MultiCoreScheduler():
    solver = PULP_CBC_CMD(msg=True)

    def __init__(self):
        self.tasks = None
        self.tasks_instances = None
        self.cores = None
        self.assigned = None
        self.start_time = None
        self.end_time = None
    
    def multicore_core_scheduler(self, system, path):
        prob = LpProblem("Multicore_Core_Scheduling", LpMinimize)
        taskPeriods = [task['period'] for task in system['EntityStore']]
        self.tasks = [task for task in system['EntityStore']]

        hyperPeriod = math.lcm(*taskPeriods)
        makespan = system['PluginParameters']['Makespan']
        schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod
        N = schedulingWindow

        self.tasks_instances = (self.create_task_instances(makespan)
            if not system['EntityInstancesStore']
            else [instance for instance in system['EntityInstancesStore']])
        
        self.cores = [core for core in system['CoreStore']]

        for i, core in enumerate(self.cores):
            core['id'] = i

        # Variables
        # 1.1 Variable for task instances, and their core assignment
        self.assigned = LpVariable.dicts("task_core",
                            ((instance['name'], value['instance'], core['name'])
                            for instance in self.tasks_instances for value in instance['value']
                            for core in self.cores),
                            lowBound=0, upBound=1, cat='Binary')

        # 1.2.1 Variable for execution start time for each instance. (s_(i,j))
        self.start_time = LpVariable.dicts("s", 
                            ((instance['name'], value['instance']) 
                            for instance in self.tasks_instances for value in instance['value']),
                            lowBound=0, cat='Integer')
        
        # 1.2.2 Variable for execution end time for each instance. (e_(i,j))
        self.end_time = LpVariable.dicts("e", 
                            ((instance['name'], value['instance']) 
                            for instance in self.tasks_instances for value in instance['value']),
                            lowBound=0, cat='Integer')
        
        # ψ_(i,j,i',j')
        # The matrices are symmetrical, which is why only the half of it is being considered for optimisation purposes.
        self.four_term_psi = LpVariable.dicts("psi_4",
                            [(task1['name'], value1['instance'],
                            task2['name'], value2['instance'],)
                            for i, task1 in enumerate(self.tasks_instances[:-1])
                            for task2 in self.tasks_instances[i+1:]
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")

        # ψ_(i,j,k,i',j',k')
        six_term_psi = LpVariable.dicts("psi_6",
                            [(task1['name'], value1['instance'], core1['name'],
                            task2['name'], value2['instance'], core2['name'])
                            for core1 in self.cores
                            for core2 in self.cores
                            for task1 in self.tasks_instances
                            for task2 in self.tasks_instances
                            if task1 != task2
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")
        
        # b_(i,j,i',j')^task
        bool_task = LpVariable.dicts("bool_task", 
                            [(task1['name'], value1['instance'],
                            task2['name'], value2['instance'])
                            for i, task1 in enumerate(self.tasks_instances[:-1])
                            for task2 in self.tasks_instances[i+1:]
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")
        
        # Constraint
        # 2.1 A task instance can have exactly one core assigned to it. (From C1 - C17)
        for task in self.tasks_instances:
            for instance in task['value']:
                prob += lpSum(self.assigned[(task['name'], instance['instance'], core['name'])] for core in self.cores) == 1

        # 2.2 All task instances under one task should have the same core assigned to it. (From C18 - C31)
        for task in self.tasks_instances:
            for i in range(len(task['value']) - 1):
                prob += lpSum(self.assigned[(task['name'], task['value'][i]['instance'], core['name'])] * core['id'] 
                              for core in self.cores) == lpSum(self.assigned[(task['name'], task['value'][i + 1]['instance'], core['name'])] * core['id'] 
                                                          for core in self.cores)
                
        # 2.3 A task's execution start time must be less than or equal to execution end time. (From C32 - C48)
        for task in self.tasks_instances:
            for instance in task['value']:
                instance_name = (task['name'], instance['instance'])
                prob += self.start_time[instance_name] <= self.end_time[instance_name]

        # 2.4 A task' total execution time must be equal to the specified execution time. (From C49 - C82)
        for task in self.tasks_instances:
            wcet = self.get_wcet(task['name'])
            for instance in task['value']:
                for core in self.cores:
                    instance_name = (task['name'], instance['instance'])
                    prob += self.end_time[instance_name] - self.start_time[instance_name] == wcet

        # 2.5.1 A task's execution start time must be greater than or equal to its LET start time,
        # 2.5.2 A task's execution end time must be less than or equal to its LET end time. (From C83 - C150)
        for task in self.tasks_instances:
            for instance in task['value']:
                for core in self.cores:
                    instance_name = (task['name'], instance['instance'])
                    prob += self.start_time[instance_name] >= instance['letStartTime']
                    prob += self.end_time[instance_name] <= instance['letEndTime']

        # 2.6 Execution intervals for the task instances on the same core should not overlap.
        # 2.6.1 (From C151 - C790)
        for core1 in self.cores:
            for core2 in self.cores:
                for i in range(len(self.tasks_instances) - 1):
                    for j in range(i + 1, len(self.tasks_instances)):
                        for instance_i in self.tasks_instances[i]['value']:
                            for instance_j in self.tasks_instances[j]['value']:
                                task_x = (self.tasks_instances[i]['name'], instance_i['instance'], core1['name'])
                                task_y = (self.tasks_instances[j]['name'], instance_j['instance'], core2['name'])
                                task_pair = (task_x + task_y)

                                prob += six_term_psi[task_pair] <= self.assigned[task_x]
                                prob += six_term_psi[task_pair] <= self.assigned[task_y]

        # 2.6.2 (From C701 - C950)
        for i in range(len(self.tasks_instances) - 1):
            for j in range(i + 1, len(self.tasks_instances)):
                for instance_i in self.tasks_instances[i]['value']:
                    for instance_j in self.tasks_instances[j]['value']:
                        four_term = (self.tasks_instances[i]['name'], instance_i['instance'], self.tasks_instances[j]['name'], instance_j['instance'])

                        prob += (self.four_term_psi[four_term] == 
                                        lpSum(six_term_psi[self.tasks_instances[i]['name'], instance_i['instance'], core1['name'], 
                                            self.tasks_instances[j]['name'], instance_j['instance'], core2['name']] 
                                            for core1 in self.cores
                                            for core2 in self.cores
                                            if core1 != core2))

        # 2.6.3 (From C951 - C1110)
        for i in range(len(self.tasks_instances) - 1):
            for j in range(i + 1, len(self.tasks_instances)):
                for instance_i in self.tasks_instances[i]['value']:
                    for instance_j in self.tasks_instances[j]['value']:
                        task_x = (self.tasks_instances[i]['name'], instance_i['instance'])
                        task_y = (self.tasks_instances[j]['name'], instance_j['instance'])
                        task_pair = (task_x + task_y)

                        prob += self.end_time[task_x] - self.start_time[task_y] <= N * bool_task[task_pair] + N * self.four_term_psi[task_pair]
                        prob += self.end_time[task_y] - self.start_time[task_x] <= N - N * bool_task[task_pair] + N * self.four_term_psi[task_pair]

        if path == '/min-core-usage':
            objective = MinCoreUsage()
            objective.min_core_usage(self.assigned, self.cores, self.tasks_instances, prob)
        elif path == '/min-e2e-mc':
            objective = MinE2EMC()
            objective.min_e2e_mc(N, system, prob, six_term_psi, self)

        # prob.solve()

        # self.update_schedule()

        # schedule = { "EntityInstancesStore" : self.tasks_instances }
                        
        # for v in prob.variables():
        #     print(f"{v.name} = {v.varValue}")

        # print(prob.sol_status)

        # return prob.sol_status, schedule
    

    def update_schedule(self):
        for task in self.tasks_instances:
            for instance in task['value']:
                for core in self.cores:
                    if self.assigned[(task['name'], instance['instance'], core['name'])].varValue == 1:
                        start_time = self.start_time[(task['name'], instance['instance'])].varValue
                        end_time = self.end_time[(task['name'], instance['instance'])].varValue

                        execution_time = [{
                            "core": core['name'],
                            "endTime": end_time,
                            "startTime": start_time
                        }]
                        instance['executionTime'] = self.get_wcet(task['name'])
                        instance['currentCore'] = core
                        instance['executionIntervals'] = execution_time


    def create_task_instances(self, makespan):
        task_instances = []

        for task in self.tasks:
            instances = []
            number_of_instances = math.ceil((makespan - task['initialOffset']) / task['period'])
            
            for i in range(0, number_of_instances):
                instances.append(self.create_task_instance(task, i))

            data = {
                "name": task['name'],
                "type": "task",
                "initialOffset": task['initialOffset'],
                "value": instances
            }
            
            task_instances.append(data)
        
        return task_instances


    def create_task_instance(self, task, index):
        periodStartTime = (index * task['period']) + task['initialOffset']
        periodEndTime = periodStartTime + task['period']
        letStartTime = periodStartTime + task['activationOffset']
        letEndTime = letStartTime + task['duration']

        return {
            "instance": index,
            "periodStartTime": periodStartTime,
            "periodEndTime": periodEndTime,
            "letStartTime": letStartTime,
            "letEndTime": letEndTime,
            "executionTime": task['wcet']
        }


    def get_wcet(self, task_name):
        return next((task for task in self.tasks if task['name'] == task_name))['wcet']