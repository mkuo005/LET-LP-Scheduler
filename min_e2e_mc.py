from pulp import LpVariable, lpSum

class MinE2EMC:
    def min_e2e_mc(self, N, system, prob, six_term_psi, mcs):
        devices = {device['name']: delay['wcdt']
                   for device in system['DeviceStore']
                   for delay in device['delays']}
        networkDelays = {networkDelay['name']: networkDelay['wcdt']
                         for networkDelay in system['NetworkDelayStore']}
        dependencies = [dependency for dependency in system['DependencyStore'] 
                        if 'system' not in dependency['source']['task'] 
                        and 'system' not in dependency['destination']['task']]
        
        # Variable
        # delta
        delta = LpVariable.dicts("delta",
                [(task1['name'], value1['instance'],
                task2['name'], value2['instance'],)
                for task1 in mcs.tasks_instances
                for task2 in mcs.tasks_instances
                if task1 != task2
                for value1 in task1['value']
                for value2 in task2['value']],
                lowBound=0, upBound=1, cat="Binary")
        
        bool_dep = LpVariable.dicts("bool_dep",
                [(task1['name'], value1['instance'],
                task2['name'], value2['instance'],)
                for task1 in mcs.tasks_instances
                for task2 in mcs.tasks_instances
                if task1 != task2
                for value1 in task1['value']
                for value2 in task2['value']],
                lowBound=0, upBound=1, cat="Binary")
        
        # Constraints
        for task1 in mcs.tasks_instances:
            for task2 in mcs.tasks_instances:
                if task1 != task2:
                    for instance1 in task1['value']:
                        for instance2 in task2['value']:
                            prob += delta == lpSum((devices[core1['device']] + 
                                                networkDelays[f"{core1['device']}-to-{core2['device']}"] + 
                                                devices[core2['device']]) *
                                                six_term_psi[task1['name'], instance1['instance'], core1['name'], 
                                                task2['name'], instance2['instance'], core2['name']]
                                                for core1 in mcs.cores
                                                for core2 in mcs.cores
                                                if core1['device'] != core2['device'])