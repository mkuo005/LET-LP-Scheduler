import math
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, getSolver

from MinCoreUsage import MinCoreUsage
from MinE2E import MinE2E

class MultiCoreScheduler:

    def __init__(self):
        self.formatted_tasks = None
        self.tasks_instances = None
        self.cores = None
        self.assigned_vars = None
        self.exec_start_vars = None
        self.exec_end_vars = None

    def multicore_core_scheduler(self, system, path, Config):
        prob = LpProblem(f"Multicore_Core_Scheduling{path}", LpMinimize)
        taskPeriods = [task["period"] for task in system["EntityStore"]]
        taskOffsets = [task["initialOffset"] for task in system["EntityStore"]]
        wcdts = [next(iter(device["delays"].values()))["wcdt"] for device in system["DeviceStore"]]
        networkDelays = [delay["wcdt"] for delay in system["NetworkDelayStore"]]
        tasks = [task for task in system["EntityStore"]]
        self.cores = [core for core in system["CoreStore"]]
        print(wcdts)

        hyperPeriod = math.lcm(*taskPeriods)
        hyperoffset = max(taskOffsets)
        hyperDelay = 2 * max(wcdts) + max(networkDelays)    # Over-approximation
        print(f"Hyper-period: {hyperPeriod}")

        # The task schedule is analysed over a scheduling window (makespan) such that 
        # all dependencies are satisfied at least once
        makespan = system["PluginParameters"]["Makespan"]
        schedulingWindow = (2 + math.ceil(hyperDelay / hyperPeriod)) * hyperPeriod + hyperoffset
        schedulingWindow = max(schedulingWindow, makespan)
        N = 2 * schedulingWindow
        print(f"Scheduling window: {schedulingWindow} ns")
        print(f"Big N: {N}")

        print("Formatted tasks")
        self.formatted_tasks = self.format_tasks(tasks, system.get("DependencyStore", None))
        for task in self.formatted_tasks:
            print(task)
        
        self.tasks_instances = self.create_task_instances(schedulingWindow, tasks, N)
        print("task instances")
        for instances in self.tasks_instances:
            for instance in instances["value"]:
                print(instance)

        # # # # # # # # # # # # #
        # Variables

        # assigned_(task,core)
        # Variable for task instances, and their core assignment. 
        self.assigned_vars = LpVariable.dicts(
            "assigned",
            [f"{instance['name']},{core['name']}" for instance in self.tasks_instances for core in self.cores],
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

        # start_(task,instance)
        # Variable for execution start time for each instance. 
        self.exec_start_vars = LpVariable.dicts(
            "start",
            [f"{instance['name']},{value['instance']}" for instance in self.tasks_instances for value in instance["value"]],
            lowBound=0,
            cat="Integer",
        )

        # end_(task,instance)
        # Variable for execution end time for each instance.
        self.exec_end_vars = LpVariable.dicts(
            "end",
            [f"{instance['name']},{value['instance']}" for instance in self.tasks_instances for value in instance["value"]],
            lowBound=0,
            cat="Integer",
        )

        # psi_tasks_(task_x,task_y)
        # Variable for whether two tasks are allocated to different cores.
        psi_tasks_vars = LpVariable.dicts(
            "psi_tasks",
            [MultiCoreScheduler.get_psi_tasks_key(task1['name'], task2['name']) for task1 in tasks for task2 in tasks if task1 != task2],
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

        # psi_task_core_(task_x,core_k,task_y,core_l)
        # Variable for the possible pairing of tasks to cores.
        psi_task_core_vars = LpVariable.dicts(
            "psi_task_core",
            [
                MultiCoreScheduler.get_psi_task_core_key(task1['name'], core1['name'], task2['name'], core2['name'])
                for core1 in self.cores for core2 in self.cores
                for task1 in self.tasks_instances for task2 in self.tasks_instances if task1 != task2
            ],
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

        # bool_task_(task_x,instance_i,task_y,instance_j)
        # Variable for whether task x executes sequentially after task y.
        bool_task_vars = LpVariable.dicts(
            "bool_task",
            [
                f"{task1['name']},{value1['instance']},{task2['name']},{value2['instance']}"
                for task1 in self.tasks_instances for task2 in self.tasks_instances if task1 != task2
                for value1 in task1["value"] for value2 in task2["value"]
            ],
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

        # # # # # # # # # # # # #
        # Constraints

        # 2a. A task's total execution time must be equal to the specified execution time.
        # 2b. A task's execution start time must be greater than or equal to its LET start time,
        # 2c. A task's execution end time must be less than or equal to its LET end time.
        for task in self.tasks_instances:
            wcet = self.get_wcet(task["name"])
            for instance in filter(lambda x: x["instance"] != -1, task["value"]):
                instance_name = f"{task['name']},{instance['instance']}"
                prob += self.exec_end_vars[instance_name] - self.exec_start_vars[instance_name] == wcet
                prob += self.exec_start_vars[instance_name] >= instance["letStartTime"]
                prob += self.exec_end_vars[instance_name] <= instance["letEndTime"]

        # 3. A task instance can only be assigned to one core.
        for task in self.tasks_instances:
            prob += lpSum(self.assigned_vars[f"{task['name']},{core['name']}"] for core in self.cores) == 1

        # 4a, 4b, 4c. Pairs of tasks are allocated to the same core when each are allocated to the same core.
        psi_task_core_considered = set()
        for core1 in self.cores:
            for core2 in self.cores:
                for task1 in self.formatted_tasks:
                    for task2 in self.formatted_tasks:
                        if task1["name"] != task2["name"]:
                            task_pair = MultiCoreScheduler.get_psi_task_core_key(task1['name'], core1['name'], task2['name'], core2['name'])
                            # Break the symmetry because task ordering does not matter.
                            if (task_pair in psi_task_core_considered): continue
                            psi_task_core_considered.add(task_pair)

                            task_x = f"{task1['name']},{core1['name']}"
                            task_y = f"{task2['name']},{core2['name']}"

                            prob += psi_task_core_vars[task_pair] <= self.assigned_vars[task_x]
                            prob += psi_task_core_vars[task_pair] <= self.assigned_vars[task_y]
                            prob += psi_task_core_vars[task_pair] >= self.assigned_vars[task_x] + self.assigned_vars[task_y] - 1

        # 4d. Pairs of tasks are not allocated to the same core when each are allocated to different cores.
        psi_tasks_considered = set()
        for task1 in self.formatted_tasks:
            for task2 in self.formatted_tasks:
                if task1["name"] != task2["name"]:
                    task_pair = MultiCoreScheduler.get_psi_tasks_key(task1['name'], task2['name'])
                    # Break the symmetry because task ordering does not matter.
                    if (task_pair in psi_tasks_considered): continue
                    psi_tasks_considered.add(task_pair)

                    prob += psi_tasks_vars[task_pair] == lpSum(
                        psi_task_core_vars[MultiCoreScheduler.get_psi_task_core_key(task1['name'], core1['name'], task2['name'], core2['name'])]
                        for core1 in self.cores for core2 in self.cores if core1 != core2
                    )

        # 5a, 5b. If task x executes after task y on the same core, x's end time must be later than y's start time 
        #         and y's end time must be earlier than x's start time.
        for task1 in self.tasks_instances:
            for task2 in self.tasks_instances:
                if task1["name"] != task2["name"]:
                    for instance1 in filter(lambda x: x["instance"] != -1, task1["value"]):
                        for instance2 in filter(lambda x: x["instance"] != -1, task2["value"]):
                            task_x = f"{task1['name']},{instance1['instance']}"
                            task_y = f"{task2['name']},{instance2['instance']}"
                            instances_pair = f"{task_x},{task_y}"
                            task_pair = MultiCoreScheduler.get_psi_tasks_key(task1['name'], task2['name'])

                            prob += self.exec_end_vars[task_x] - self.exec_start_vars[task_y] <= N * bool_task_vars[instances_pair] + N * psi_tasks_vars[task_pair]
                            prob += self.exec_end_vars[task_y] - self.exec_start_vars[task_x] <= N - N * bool_task_vars[instances_pair] + N * psi_tasks_vars[task_pair]

        if path == "/min-core-usage":
            objective = MinCoreUsage()
            objective.min_core_usage(self.assigned_vars, self.cores, self.tasks_instances, prob)
        elif path == "/min-e2e-mc":
            objective = MinE2E()
            objective.min_e2e(N, system, prob, psi_task_core_vars, self)

        prob.writeLP(Config.lpFile)
        prob.solve(getSolver(Config.solverProg))

        self.update_schedule()
        schedule = {"EntityInstancesStore": self.tasks_instances}

        for v in prob.variables():
            print(f"{v.name} = {v.varValue}")

        print(prob.sol_status)

        return prob.sol_status, schedule

    # For breaking symmetry because the task ordering does not matter.
    @staticmethod
    def get_psi_tasks_key(task1Name, task2Name):
        if task1Name < task2Name: return f"{task1Name},{task2Name}"
        else: return f"{task2Name},{task1Name}"

    # For breaking symmetry because the task ordering does not matter.
    @staticmethod
    def get_psi_task_core_key(task1Name, core1Name, task2Name, core2Name):
        if task1Name < task2Name: return f"{task1Name},{core1Name},{task2Name},{core2Name}"
        else: return f"{task2Name},{core2Name},{task1Name},{core1Name}"

    def format_tasks(self, tasks, dependencies):
        formatted_tasks = []

        for task in tasks:
            source_tasks = self.get_source_tasks(task, dependencies)

            device = self.get_device(task.get("core", None))

            data = {
                "name": task["name"],
                "offset": task["activationOffset"],
                "duration": task["duration"],
                "period": task["period"],
                "wcet": task["wcet"],
                "requiredDevice": device,
                "dependsOn": source_tasks,
            }

            formatted_tasks.append(data)

        return formatted_tasks

    def update_schedule(self):
        for task in self.tasks_instances:
            task["value"] = [instance for instance in task["value"] if instance["instance"] != -1]
            for instance in task["value"]:
                for core in self.cores:
                    if self.assigned_vars[f"{task['name']},{core['name']}"].varValue == 1:
                        start_time = self.exec_start_vars[f"{task['name']},{instance['instance']}"].varValue
                        end_time = self.exec_end_vars[f"{task['name']},{instance['instance']}"].varValue

                        execution_time = [
                            {
                                "core": core["name"],
                                "endTime": end_time,
                                "startTime": start_time,
                            }
                        ]
                        instance["executionTime"] = self.get_wcet(task["name"])
                        instance["currentCore"] = core
                        instance["executionIntervals"] = execution_time

    def create_task_instances(self, makespan, tasks, N):
        task_instances = []

        for task in tasks:
            instances = []
            number_of_instances = math.ceil((makespan - task["initialOffset"]) / task["period"])

            instances.append(self.create_negative_instance(task, N))

            for i in range(0, number_of_instances):
                instances.append(self.create_task_instance(task, i))

            data = {
                "name": task["name"],
                "type": "task",
                "initialOffset": task["initialOffset"],
                "value": instances,
            }

            task_instances.append(data)

        return task_instances

    def create_negative_instance(self, task, N):
        return {
            "instance": -1,
            "letStartTime": -N,
            "letEndTime": -N + task["duration"],
            "executionTime": task["wcet"],
        }

    def create_task_instance(self, task, index):
        periodStartTime = (index * task["period"]) + task["initialOffset"]
        periodEndTime = periodStartTime + task["period"]
        letStartTime = periodStartTime + task["activationOffset"]
        letEndTime = letStartTime + task["duration"]

        return {
            "instance": index,
            "periodStartTime": periodStartTime,
            "periodEndTime": periodEndTime,
            "letStartTime": letStartTime,
            "letEndTime": letEndTime,
            "executionTime": task["wcet"],
        }

    def get_wcet(self, task_name):
        return next((task for task in self.formatted_tasks if task["name"] == task_name))["wcet"]

    def get_device(self, core):
        return next((c["device"] for c in self.cores if c["name"] == core), None)

    def get_source_tasks(self, task, dependencies):
        source_tasks = []

        if dependencies is not None:
            for dependency in filter(lambda x: x["source"]["entity"] != "__system" and x["destination"]["entity"] != "__system", dependencies):
                if dependency["destination"]["entity"] == task["name"]:
                    source_tasks.append(dependency["source"]["entity"])

        return source_tasks
