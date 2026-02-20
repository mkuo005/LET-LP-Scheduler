from pulp import LpVariable, lpSum

class MinCoreUsage():
    def min_core_usage(self, assigned, cores, tasks_instances, prob):
        # used_core
        # Variable for whether a core is being used.
        used = LpVariable.dicts("used", ((core['name']) for core in cores), lowBound=0, upBound=1, cat='Binary')
                   
        # 6a. If a task instance uses a core, the core is marked used.
        for core in cores:
            for task in tasks_instances:
                prob += used[(core['name'])] >= assigned[f"{task['name']},{core['name']}"]

        # 7. Minimise the sum of the used cores.
        objective = lpSum(used[(core['name'])] for core in cores)
        prob += objective, "Minimise Core Usage" 
