from pulp import LpVariable, lpSum

class MinE2EMC:
    def __init__(self):
        self.network_delays = None
        self.devices = None

    def min_e2e_mc(self, N, system, prob, psi_task_core_vars, mcs):
        self.devices = {device['name']: delay['wcdt']
                   for device in system['DeviceStore']
                   for delay in device['delays']}
        self.network_delays = {networkDelay['name']: networkDelay['wcdt']
                         for networkDelay in system['NetworkDelayStore']}
        
        # Variable
        # lambda
        lambda_vars = LpVariable.dicts("lambda",
                [(task1['name'], task2['name'])
                for task1 in mcs.tasks_instances
                for task2 in mcs.tasks_instances
                if task1 != task2],
                lowBound=0, cat="Integer")
        
        bool_dep_vars = LpVariable.dicts("bool_dep",
                [(task1['name'], value1['instance'],
                task2['name'], value2['instance'],)
                for task1 in mcs.tasks_instances
                for task2 in mcs.tasks_instances
                if task1 != task2
                for value1 in task1['value']
                for value2 in task2['value']],
                lowBound=0, upBound=1, cat="Binary")
        
        delay_vars = LpVariable.dicts("delay",
                [(task1['name'], value1['instance'],
                task2['name'], value2['instance'],)
                for task1 in mcs.tasks_instances
                for task2 in mcs.tasks_instances
                if task1 != task2
                for value1 in task1['value']
                for value2 in task2['value']],
                lowBound=0, cat="Integer")
        
        # Constraints
        # 6a. in the equations doc (From C194 - C217)
        for task1 in mcs.formatted_tasks:
            for task2 in mcs.formatted_tasks:
                if task1['name'] != task2['name']:
                    task_pair = task1['name'], task2['name']
                    prob += lambda_vars[task_pair] == lpSum(psi_task_core_vars[(task1['name'], core1['name'], 
                                                                                task2['name'], core2['name'])] * self.get_delay(core1, core2, N)
                                                                                 for core1 in mcs.cores 
                                                                                 for core2 in mcs.cores)           
        
        # 6b. in the equations doc (From C218 - C229)
        for task2 in mcs.formatted_tasks:
            for depends_on in task2['dependsOn']:
                for instance2 in filter(lambda x: x['instance'] != -1, self.get_instances(task2['name'], mcs)):
                    for instance1 in self.get_instances(depends_on, mcs):
                        dep_pair = depends_on, task2['name']
                        dep_instances_pair = depends_on, instance1['instance'], task2['name'], instance2['instance']
                        prob += instance1['letEndTime'] + lambda_vars[dep_pair] - instance2['letStartTime'] <= N - N * bool_dep_vars[dep_instances_pair]
                    
                    prob += lpSum(bool_dep_vars[(depends_on, instance1['instance'], task2['name'], instance2['instance'])] 
                                  for instance1 in self.get_instances(depends_on, mcs)) == 1
        
        for task1 in mcs.tasks_instances:
            for task2 in mcs.tasks_instances:
                if task1['name'] != task2['name']:
                    for instance1 in task1['value']:
                        for instance2 in filter(lambda x: x['instance'] != -1, task2['value']):
                            dep_instances_pair = task1['name'], instance1['instance'], task2['name'], instance2['instance']
                            prob += delay_vars[dep_instances_pair] >= instance2['letStartTime'] - instance1['letEndTime'] - N + N * bool_dep_vars[dep_instances_pair]
                            prob += delay_vars[dep_instances_pair] <= instance2['letStartTime'] - instance1['letEndTime'] + N - N * bool_dep_vars[dep_instances_pair]

        objective = lpSum(delay_vars[task1['name'], value1['instance'],
                    task2['name'], value2['instance']]
                    for task1 in mcs.tasks_instances
                    for task2 in mcs.tasks_instances
                    if task1 != task2
                    for value1 in task1['value']
                    for value2 in task2['value'])
        prob += objective, "Minimise End-to-End Response Time" 

    def get_delay(self, source, dest, N):
        if source["device"] == dest["device"]:
            return 0
        
        for link in self.network_delays:
            if link == f"{source['device']}-to-{dest['device']}":
                
                comm_delay = self.network_delays[link] + self.get_device_delay(source['device']) + self.get_device_delay(dest['device'])
                return comm_delay
        
        return N

    def get_instances(self, name, mcs):
        for task in mcs.tasks_instances:
            if(task['name'] == name):
                return task['value']
            
    def get_device_delay(self, name):
        for device in self.devices:
            if device == name:
                return self.devices[device]