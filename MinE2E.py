from pulp import LpVariable, lpSum

class MinE2E:
    def __init__(self):
        self.network_delays = None
        self.devices = None

    def min_e2e(self, N, system, prob, psi_task_core_vars, mcs):
        self.devices = {device["name"]: delay["wcdt"] for device in system["DeviceStore"] for _, delay in device["delays"].items()}
        self.network_delays = {networkDelay["name"]: networkDelay["wcdt"] for networkDelay in system["NetworkDelayStore"]}

        # # # # # # # # # # # # #
        # Variables

        # lambda_(task_x, task_y)
        # Variable for just the protocol + network component of the communication delay from task x to task y.
        lambda_vars = LpVariable.dicts(
            "lambda",
            [f"{task1['name']},{task2['name']}" for task1 in mcs.tasks_instances for task2 in mcs.tasks_instances if task1 != task2],
            lowBound=0,
            cat="Integer",
        )

        # bool_dep_(task_x, instance_i, task_y, instance_j)
        # Variable for whether there is a communication dependency from task x, instance i to task y, instance j.
        bool_dep_vars = LpVariable.dicts(
            "bool_dep",
            [
                f"{task1['name']},{value1['instance']},{task2['name']},{value2['instance']}"
                for task1 in mcs.tasks_instances for task2 in mcs.tasks_instances if task1 != task2
                for value1 in task1["value"] for value2 in task2["value"]
            ],
            lowBound=0,
            upBound=1,
            cat="Binary",
        )

        # delay_(task_x, instance_i, task_y, instance_j)
        # Variable for the entire communication delay (including waiting for the data to be consumed) from task x, instance i to task y, instance j.
        delay_vars = LpVariable.dicts(
            "delay",
            [
                f"{task1['name']},{value1['instance']},{task2['name']},{value2['instance']}"
                for task1 in mcs.tasks_instances for task2 in mcs.tasks_instances if task1 != task2
                for value1 in task1["value"] for value2 in task2["value"]
            ],
            lowBound=0,
            cat="Integer",
        )

        # # # # # # # # # # # # #
        # Constraints
        
        # 8b. Aggregate the protocol + network component of the communication delays.
        for task1 in mcs.formatted_tasks:
            for task2 in mcs.formatted_tasks:
                if task1["name"] != task2["name"]:
                    task_pair = f"{task1['name']},{task2['name']}"
                    prob += lambda_vars[task_pair] == lpSum(
                        psi_task_core_vars[mcs.get_psi_task_core_key(task1['name'], core1['name'], task2['name'], core2['name'])] * self.get_delay(core1, core2, N)
                        for core1 in mcs.cores for core2 in mcs.cores
                    )

        # 8e. The source's end time must allow for the protocol + network component of the communication delay to be handled.
        # 8f. The destination's communication dependency can only be satisfied by one source.
        for task2 in mcs.formatted_tasks:
            for depends_on in task2["dependsOn"]:
                for instance2 in filter(lambda x: x["instance"] != -1, self.get_instances(task2["name"], mcs)):
                    for instance1 in self.get_instances(depends_on, mcs):
                        dep_pair = f"{depends_on},{task2['name']}"
                        dep_instances_pair = f"{depends_on},{instance1['instance']},{task2['name']},{instance2['instance']}"
                        prob += instance1["letEndTime"] + lambda_vars[dep_pair] - instance2["letStartTime"] <= N - N * bool_dep_vars[dep_instances_pair]

                    prob += (
                        lpSum(
                            bool_dep_vars[f"{depends_on},{instance1['instance']},{task2['name']},{instance2['instance']}"]
                            for instance1 in self.get_instances(depends_on, mcs)
                        ) == 1
                    )
        # 9a, 9b. Calculate the exact communication delay of the selected communication dependency.
        for task1 in mcs.tasks_instances:
            for task2 in mcs.tasks_instances:
                if task1["name"] != task2["name"]:
                    for instance1 in task1["value"]:
                        for instance2 in filter(lambda x: x["instance"] != -1, task2["value"]):
                            dep_instances_pair = f"{task1['name']},{instance1['instance']},{task2['name']},{instance2['instance']}"
                            prob += (delay_vars[dep_instances_pair] >= instance2["letStartTime"] - instance1["letEndTime"] - N + N * bool_dep_vars[dep_instances_pair])
                            prob += (delay_vars[dep_instances_pair] <= instance2["letStartTime"] - instance1["letEndTime"] + N - N * bool_dep_vars[dep_instances_pair])

        # 10. Minimise the response times.
        objective = lpSum(
            delay_vars[f"{task1['name']},{value1['instance']},{task2['name']},{value2['instance']}"]
            for task1 in mcs.tasks_instances for task2 in mcs.tasks_instances if task1 != task2
            for value1 in task1["value"] for value2 in task2["value"]
        )
        prob += objective, "Minimise End-to-End Response Time"

    # Equation 8a. Calculate the protocol + network component of a communication delay.
    def get_delay(self, source, dest, N):
        if source["device"] == dest["device"]:
            return 0

        for link in self.network_delays:
            if link == f"{source['device']}-to-{dest['device']}":
                comm_delay = self.network_delays[link] + self.get_device_delay(source["device"]) + self.get_device_delay(dest["device"])
                return comm_delay

        return N

    def get_instances(self, name, mcs):
        for task in mcs.tasks_instances:
            if task["name"] == name:
                return task["value"]

    def get_device_delay(self, name):
        for device in self.devices:
            if device == name:
                return self.devices[device]
