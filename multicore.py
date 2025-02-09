import math
from pulp import PULP_CBC_CMD, LpProblem, LpMinimize, LpVariable, lpSum

class MultiCoreScheduler():
    solver = PULP_CBC_CMD(msg=True)

    def __init__(self):
        self.prob = LpProblem("Multicore_Core_Scheduling", LpMinimize)
        self.system = None
        self.taskInstances = None
        self.cores = None
        self.a = None
        self.six_term_psi = None
        self.s = None
        self.e = None
    
    def multicore_core_scheduler(self, system):
        self.system = system
        taskPeriods = [task['period'] for task in system['EntityStore']]
        self.tasks = [instance for instance in system['EntityInstancesStore']]
        tasks = [task for task in system['EntityStore']]
        self.cores = [core for core in system['CoreStore']]

        hyperPeriod = math.lcm(*taskPeriods)
        makespan = system['PluginParameters']['Makespan']
        schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod
        N = schedulingWindow

        for i, core in enumerate(self.cores):
            core['id'] = i

        # Variables
        # 1.1 Variable for each task instance, and a core. (a_(i,j,k))
        self.a = LpVariable.dicts("task_core",
                            ((instance['name'], value['instance'], core['name'])
                            for instance in self.tasks for value in instance['value']
                            for core in self.cores),
                            lowBound=0, upBound=1, cat='Binary')

        # 1.2.1 Variable for execution start time for each instance. (s_(i,j))
        self.s = LpVariable.dicts("s", 
                            ((instance['name'], value['instance']) 
                            for instance in self.tasks for value in instance['value']),
                            lowBound=0, cat='Integer')
        
        # 1.2.2 Variable for execution end time for each instance. (e_(i,j))
        self.e = LpVariable.dicts("e", 
                            ((instance['name'], value['instance']) 
                            for instance in self.tasks for value in instance['value']),
                            lowBound=0, cat='Integer')
        
        # 1.3 Variable to track if a core is being used. (u_j)
        u = LpVariable.dicts("u", ((core['name']) for core in self.cores), 
                             lowBound=0, upBound=1, cat='Binary')
        
        # ψ_(i,j,i',j')
        # The matrices are symmetrical, which is why only the half of it is being considered for optimisation purposes.
        self.four_term_psi = LpVariable.dicts("psi_4",
                            [(task1['name'], value1['instance'],
                            task2['name'], value2['instance'],)
                            for i, task1 in enumerate(self.tasks[:-1])
                            for task2 in self.tasks[i+1:]
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")

        # ψ_(i,j,k,i',j',k')
        self.six_term_psi = LpVariable.dicts("psi_6",
                            [(task1['name'], value1['instance'], core1['name'],
                            task2['name'], value2['instance'], core2['name'])
                            for core1 in self.cores
                            for core2 in self.cores
                            for i, task1 in enumerate(self.tasks[:-1])
                            for task2 in self.tasks[i+1:]
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")
        
        # b_(i,j,i',j')^task
        b = LpVariable.dicts("b", 
                            [(task1['name'], value1['instance'],
                            task2['name'], value2['instance'])
                            for i, task1 in enumerate(self.tasks[:-1])
                            for task2 in self.tasks[i+1:]
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")
        
        # Constraint
        # 2.1 A task instance can have exactly one core assigned to it.
        for task in self.tasks:
            for instance in task['value']:
                self.prob += lpSum(self.a[(task['name'], instance['instance'], core['name'])] for core in self.cores) == 1

        # 2.2 All task instances under one task should have the same core assigned to it.
        for task in self.tasks:
            for i in range(len(task['value']) - 1):
                self.prob += lpSum(self.a[(task['name'], task['value'][i]['instance'], core['name'])] * core['id'] 
                              for core in self.cores) == lpSum(self.a[(task['name'], task['value'][i + 1]['instance'], core['name'])] * core['id'] 
                                                          for core in self.cores)
                
        # 2.3 A task's execution start time must be less than or equal to execution end time.
        for task in self.tasks:
            for instance in task['value']:
                instance_name = (task['name'], instance['instance'])
                self.prob += self.s[instance_name] <= self.e[instance_name]

        # 2.4 A task' total execution time must be equal to the specified execution time.
        for task in self.tasks:
            for instance in task['value']:
                for core in self.cores:
                    instance_name = (task['name'], instance['instance'])
                    self.prob += self.e[instance_name] - self.s[instance_name] == instance['executionTime']

        # 2.5.1 A task's execution start time must be greater than or equal to its LET start time,
        # 2.5.2 A task's execution end time must be less than or equal to its LET end time.
        for task in self.tasks:
            for instance in task['value']:
                for core in self.cores:
                    instance_name = (task['name'], instance['instance'])
                    self.prob += self.s[instance_name] >= instance['letStartTime']
                    self.prob += self.e[instance_name] <= instance['letEndTime']

        # 2.6 Execution intervals for the task instances on the same core should not overlap.
        # 2.6.1
        for core1 in self.cores:
            for core2 in self.cores:
                for i in range(len(self.tasks) - 1):
                    for j in range(i + 1, len(self.tasks)):
                        for instance_i in self.tasks[i]['value']:
                            for instance_j in self.tasks[j]['value']:
                                task_x = (self.tasks[i]['name'], instance_i['instance'], core1['name'])
                                task_y = (self.tasks[j]['name'], instance_j['instance'], core2['name'])
                                task_pair = (task_x + task_y)

                                self.prob += self.six_term_psi[task_pair] <= self.a[task_x]
                                self.prob += self.six_term_psi[task_pair] <= self.a[task_y]

        # 2.6.2
        for i in range(len(self.tasks) - 1):
            for j in range(i + 1, len(self.tasks)):
                for instance_i in self.tasks[i]['value']:
                    for instance_j in self.tasks[j]['value']:
                        for core1 in self.cores:
                                four_term = (self.tasks[i]['name'], instance_i['instance'], self.tasks[j]['name'], instance_j['instance'])

                                self.prob += (self.four_term_psi[four_term] == 
                                              lpSum(self.six_term_psi[self.tasks[i]['name'], instance_i['instance'], core1['name'], 
                                                    self.tasks[j]['name'], instance_j['instance'], core2['name']] 
                                                    for core2 in self.cores
                                                    if core1 != core2))

        # 2.6.3
        for i in range(len(self.tasks) - 1):
            for j in range(i + 1, len(self.tasks)):
                for instance_i in self.tasks[i]['value']:
                    for instance_j in self.tasks[j]['value']:
                        task_x = (self.tasks[i]['name'], instance_i['instance'])
                        task_y = (self.tasks[j]['name'], instance_j['instance'])
                        task_pair = (task_x + task_y)

                        self.prob += self.e[task_x] - self.s[task_y] <= N * b[task_pair] + N * self.four_term_psi[task_pair]
                        self.prob += self.e[task_y] - self.s[task_x] <= N - N * b[task_pair] + N * self.four_term_psi[task_pair]
                            
        # 8. If a task instance uses a core, the core is marked used. (Generated by ChatGPT)
        for core in self.cores:
            for task in self.tasks:
                for instance in task['value']:
                    self.prob += self.a[(task['name'], instance['instance'], core['name'])] <= u[(core['name'])]

        if (self.system['DependencyStore'] == None):
            objective = lpSum(u[(core['name'])] for core in self.cores)
            self.prob += objective, "Minimise Core Usage"
        else:
            self.dependency_constraints()

        print(self.prob)

        self.prob.solve()

        self.update_schedule()

        schedule = { "EntityInstancesStore" : self.tasks }

        # print(schedule)
                        
        for v in self.prob.variables():
            print(f"{v.name} = {v.varValue}")

        print(self.prob.sol_status)

        return self.prob.sol_status, schedule
    
    def dependency_constraints(self):
        devices = [(device['name'], delay['wcdt'])
                   for device in self.system['DeviceStore']
                   for delay in device['delays']]
        networkDelays = [(networkDelay['name'], networkDelay['wcdt']) for networkDelay in self.system['NetworkDelayStore']]
        dependencies = [dependency for dependency in self.system['DependencyStore'] 
                        if 'system' not in dependency['source']['task'] 
                        and 'system' not in dependency['destination']['task']]
        
        # Variable
        # Dependency time
        delay = LpVariable.dicts("delay",
                                [(dependency['source']['task'], core1['name'], 
                                dependency['destination']['task'], core2['name'])
                                for core1 in self.cores
                                for core2 in self.cores
                                for dependency in dependencies],
                                lowBound=0, cat='Integer')
        
        # Constraints
        # TODO: Make it so it uses all the task instances (entire makespan)
        for dependency in dependencies:
            for core1 in self.cores:
                for core2 in self.cores:
                    source = dependency['source']['task']
                    dest = dependency['destination']['task']
                    sourceEnd = next(task for task in self.tasks if task['name'] == source)['value'][0]['letEndTime']
                    destTask = next(task for task in self.tasks if task['name'] == dest)

                    sourceDevice = next(core['device'] for core in self.cores if core['name'] == core1['name'])
                    destDevice = next(core['device'] for core in self.cores if core['name'] == core2['name'])
                    
                    # If cores are on different devices, the dependency will have additional transmission delays.
                    if (sourceDevice != destDevice):
                        sourceDelay = next(device for device in devices if device[0] == sourceDevice)[1]
                        destDelay = next(device for device in devices if device[0] == destDevice)[1]
                        networkDelay = next(delay for delay in networkDelays if delay[0] == f'{sourceDevice}-to-{destDevice}')[1]
                        totalDelay = sourceDelay + destDelay + networkDelay
                        destStart = next(instance for instance in destTask['value'] if instance['letStartTime'] >= sourceEnd + totalDelay)['letStartTime']
                        depDelay = destStart - sourceEnd
                        
                        self.prob += delay[source, core1['name'], dest, core2['name']] == self.six_term_psi[source, 0, core1['name'], dest, 0, core2['name']] * depDelay

                    # If cores are on same devices, the dependency's delay will only be the time between a pair of tasks.
                    else:
                        destStart = next(instance for instance in destTask['value'] if instance['letStartTime'] >= sourceEnd)['letStartTime']
                        depDelay = destStart - sourceEnd
                        
                        self.prob += delay[source, core1['name'], dest, core2['name']] == self.six_term_psi[source, 0, core1['name'], dest, 0, core2['name']] * depDelay

        # Objective
        objective = lpSum(delay[dependency['source']['task'], core1['name'], 
                            dependency['destination']['task'], core2['name']]
                            for core1 in self.cores
                            for core2 in self.cores
                            for dependency in dependencies)
        self.prob += objective, "Minimise Transmission Delay"

    def update_schedule(self):
        for instance in self.tasks:
            for value in instance['value']:
                for core in self.cores:
                    if self.a[(instance['name'], value['instance'], core['name'])].varValue == 1:
                        start_time = self.s[(instance['name'], value['instance'])].varValue
                        end_time = self.e[(instance['name'], value['instance'])].varValue

                        execution_time = {
                            "core": core['name'],
                            "endTime": end_time,
                            "startTime": start_time
                        }

                        value['currentCore'] = core['name']
                        value['executionIntervals'] = execution_time