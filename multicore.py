import math
from pulp import PULP_CBC_CMD, LpProblem, LpMinimize, LpVariable, lpSum

from min_core_usage import MinCoreUsage
from min_e2e_mc import MinE2EMC

class MultiCoreScheduler():
    solver = PULP_CBC_CMD(msg=True)

    def __init__(self):
        self.formatted_tasks = None
        self.tasks_instances = None
        self.cores = None
        self.assigned_vars = None
        self.exec_start_vars = None
        self.exec_end_vars = None
    
    def multicore_core_scheduler(self, system, path):
        prob = LpProblem("Multicore_Core_Scheduling", LpMinimize)
        taskPeriods = [task['period'] for task in system['EntityStore']]
        tasks = [task for task in system['EntityStore']]
        self.cores = [core for core in system['CoreStore']]

        hyperPeriod = math.lcm(*taskPeriods)
        makespan = system['PluginParameters']['Makespan']
        schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod
        N = schedulingWindow

        self.formatted_tasks = self.format_tasks(tasks, system.get('DependencyStore', None))
        self.tasks_instances = self.create_task_instances(makespan, tasks, N)
        
        # Variables
        # Variable for task instances, and their core assignment
        self.assigned_vars = LpVariable.dicts("assigned",
                            ((instance['name'], core['name'])
                            for instance in self.tasks_instances
                            for core in self.cores),
                            lowBound=0, upBound=1, cat='Binary')

        # Variable for execution start time for each instance. (s_(i,j))
        self.exec_start_vars = LpVariable.dicts("start", 
                            ((instance['name'], value['instance']) 
                            for instance in self.tasks_instances for value in instance['value']),
                            lowBound=0, cat='Integer')
        
        # Variable for execution end time for each instance. (e_(i,j))
        self.exec_end_vars = LpVariable.dicts("end", 
                            ((instance['name'], value['instance']) 
                            for instance in self.tasks_instances for value in instance['value']),
                            lowBound=0, cat='Integer')
        
        # ψ_(x,y)^core
        # The matrices are symmetrical, which is why only the half of it is being considered for optimisation purposes.
        psi_tasks_vars = LpVariable.dicts("psi_tasks",
                        [(task1['name'], task2['name'])
                        for task1 in tasks
                        for task2 in tasks
                        if task1 != task2],
                        lowBound=0, upBound=1, cat="Binary")

        # ψ_(x,k,y,l)^core
        psi_task_core_vars = LpVariable.dicts("psi_task_core",
                            [(task1['name'], core1['name'],
                            task2['name'], core2['name'])
                            for core1 in self.cores
                            for core2 in self.cores
                            for task1 in self.tasks_instances
                            for task2 in self.tasks_instances
                            if task1 != task2],
                            lowBound=0, upBound=1, cat="Binary")
        
        # b_(x,i,y,j)^task
        bool_task_vars = LpVariable.dicts("bool_task", 
                            [(task1['name'], value1['instance'],
                            task2['name'], value2['instance'])
                            for task1 in self.tasks_instances
                            for task2 in self.tasks_instances
                            if task1 != task2
                            for value1 in task1['value']
                            for value2 in task2['value']],
                            lowBound=0, upBound=1, cat="Binary")
        
        # Constraint
        # 1. A task instance can have exactly one core assigned to it. (From C1 - C17)
        for task in self.tasks_instances:
                prob += lpSum(self.assigned_vars[(task['name'], core['name'])] for core in self.cores) == 1

        # 2b. A task' total execution time must be equal to the specified execution time. (From C49 - C82)
        # 2c. A task's execution start time must be greater than or equal to its LET start time,
        # 2d. A task's execution end time must be less than or equal to its LET end time. (From C83 - C150)
        for task in self.tasks_instances:
            wcet = self.get_wcet(task['name'])
            for instance in filter(lambda x: x['instance'] != -1, task['value']):
                instance_name = (task['name'], instance['instance'])
                prob += self.exec_end_vars[instance_name] - self.exec_start_vars[instance_name] == wcet
                prob += self.exec_start_vars[instance_name] >= instance['letStartTime']
                prob += self.exec_end_vars[instance_name] <= instance['letEndTime']

        # 3a. Execution intervals for the task instances on the same core should not overlap. (From C151 - C790)
        for core1 in self.cores:
            for core2 in self.cores:
                for task1 in self.formatted_tasks:
                    for task2 in self.formatted_tasks:
                        if task1['name'] != task2['name']:
                            task_x = task1['name'], core1['name']
                            task_y = task2['name'], core2['name']
                            task_pair = (task_x + task_y)

                            prob += psi_task_core_vars[task_pair] <= self.assigned_vars[task_x]
                            prob += psi_task_core_vars[task_pair] <= self.assigned_vars[task_y]
                            prob += psi_task_core_vars[task_pair] >= self.assigned_vars[task_x] + self.assigned_vars[task_y] - 1

        # 3b. (From C701 - C950)
        for task1 in self.formatted_tasks:
            for task2 in self.formatted_tasks:
                if task1['name'] != task2['name']:
                    task_pair = (task1['name'], task2['name'])

                    prob += (psi_tasks_vars[task_pair] == 
                                    lpSum(psi_task_core_vars[task1['name'], core1['name'], 
                                        task2['name'], core2['name']] 
                                        for core1 in self.cores
                                        for core2 in self.cores
                                        if core1 != core2))

        # 3c, 3d. (From C951 - C1110)
        for task1 in self.tasks_instances:
            for task2 in self.tasks_instances:
                    if task1['name'] != task2['name']:
                        for instance1 in filter(lambda x: x['instance'] != -1, task1['value']):
                            for instance2 in filter(lambda x: x['instance'] != -1, task2['value']):
                                task_x = (task1['name'], instance1['instance'])
                                task_y = (task2['name'], instance2['instance'])
                                instances_pair = (task_x + task_y)
                                task_pair = (task1['name'], task2['name'])

                                prob += self.exec_end_vars[task_x] - self.exec_start_vars[task_y] <= N * bool_task_vars[instances_pair] + N * psi_tasks_vars[task_pair]
                                prob += self.exec_end_vars[task_y] - self.exec_start_vars[task_x] <= N - N * bool_task_vars[instances_pair] + N * psi_tasks_vars[task_pair]

        if path == '/min-core-usage':
            objective = MinCoreUsage()
            objective.min_core_usage(self.assigned_vars, self.cores, self.tasks_instances, prob)
        elif path == '/min-e2e-mc':
            objective = MinE2EMC()
            objective.min_e2e_mc(N, system, prob, psi_task_core_vars, self)

        print(prob)

        prob.solve()

        self.update_schedule()

        schedule = { "EntityInstancesStore" : self.tasks_instances }
                        
        for v in prob.variables():
            print(f"{v.name} = {v.varValue}")

        print(prob.sol_status)

        return prob.sol_status, schedule
    

    def format_tasks(self, tasks, dependencies):
        formatted_tasks = []

        for task in tasks:
            source_tasks = self.get_source_tasks(task, dependencies)
            
            device = self.get_device(task.get('core', None))

            data = {
                "name": task['name'],
                "offset": task['activationOffset'],
                "duration": task['duration'],
                "period": task['period'],
                "wcet": task['wcet'],
                "requiredDevice": device,
                "dependsOn": source_tasks
            }

            formatted_tasks.append(data)

        return formatted_tasks


    def update_schedule(self):
        for task in self.tasks_instances:
            task['value'] = [instance for instance in task['value'] if instance['instance'] != -1]
            for instance in task['value']:
                for core in self.cores:
                    if self.assigned_vars[(task['name'], core['name'])].varValue == 1:
                        start_time = self.exec_start_vars[(task['name'], instance['instance'])].varValue
                        end_time = self.exec_end_vars[(task['name'], instance['instance'])].varValue

                        execution_time = [{
                            "core": core['name'],
                            "endTime": end_time,
                            "startTime": start_time
                        }]
                        instance['executionTime'] = self.get_wcet(task['name'])
                        instance['currentCore'] = core
                        instance['executionIntervals'] = execution_time


    def create_task_instances(self, makespan, tasks, N):
        task_instances = []

        for task in tasks:
            instances = []
            number_of_instances = math.ceil((makespan - task['initialOffset']) / task['period'])

            instances.append(self.create_negative_instance(task, N))
            
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

    def create_negative_instance(self, task, N):
        return {
            "instance": -1,
            "letStartTime": -N,
            "letEndTime": -N + task['duration'],
            "executionTime": task['wcet']
        }


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
        return next((task for task in self.formatted_tasks if task['name'] == task_name))['wcet']


    def get_device(self, core):
        return next((c['device'] for c in self.cores if c['name'] == core), None)


    def get_source_tasks(self, task, dependencies):
        source_tasks = []

        if dependencies is not None:
            for dependency in filter(lambda x: x['source']['task'] != '__system' and x['destination']['task'] != '__system', dependencies):
                if dependency['destination']['task'] == task['name']:
                    source_tasks.append(dependency['source']['task'])

        return source_tasks
