import pulp as pl
class  PuLPWriter:
    equations = [{}]
    
    def listAvalaibleSolvers(self):
        solver_list = pl.listSolvers(onlyAvailable=True)
        print("Avaliable Solver on System:" + solver_list)
        print("Supported Solvers: "+pl.listSolvers())

    def __init__(self, filename, objectiveVariable, lpLargeConstant):
        self.prob = pl.LpProblem(filename, pl.LpMinimize)
        self.filename = filename
        self.objectiveVariable = pl.LpVariable(objectiveVariable, None, None, pl.LpInteger)
        self.lpLargeConstant = lpLargeConstant
        
        self.dependencyInstanceDelayVariables = {}
        
        # All variables
        self.vars = {}


    def writeComment(self, string):
        None

    def writeObjective(self):
        self.prob += self.objectiveVariable #Expressions are objectives

    def writeObjectiveEquation(self):
        #dependencyInstanceDelays = ' - '.join([x for v in self.dependencyInstanceDelayVariables.values() for x in v])
        #self.write(f"{self.objectiveVariable} - {dependencyInstanceDelays} = 0;\n", "Objective equation")
        #print([self.getIntVar(x) for v in self.dependencyInstanceDelayVariables.values() for x in v])
        self.prob += self.objectiveVariable == pl.lpSum([self.getIntVar(x) for v in self.dependencyInstanceDelayVariables.values() for x in v])

    def taskInstStartTime(self, taskInstance):
        return f"U{taskInstance}_start_time"
    
    def taskInstEndTime(self, taskInstance):
        return f"U{taskInstance}_end_time"
    
    def getIntVar(self, name):
        if (name in self.vars) == False:
            lpVar = pl.LpVariable(name, None, None, pl.LpInteger)
            self.vars[name] = lpVar
        return self.vars[name]
    
    def getBoolVar(self, name):
        if (name in self.vars) == False:
            lpVar = pl.LpVariable(name, None, None, pl.LpBinary)
            self.vars[name] = lpVar
        return self.vars[name]
    
    # Equation 2
    # Create constraints to compute task instance start and end times for each task instance (i) within the scheduling window
    def createTaskInstancesAsConstraints(self, system, schedulingWindow, Config):
        allTaskInstances = {}
        for task in system['TaskStore']:
            # Get task parameters
            taskName = task['name']
            taskWcet = task['wcet']
            taskPeriod = task['period']
            
            self.writeComment(f"Task instance properties of {taskName}")
            
            # Create the task instances that appear inside the scheduling window
            instances = []

            # instancePeriodStartTime is 𝑖 × 𝑡.𝑝
            for instancePeriodStartTime in range(0, schedulingWindow, taskPeriod):
                # Task instance name includes an instance number
                instanceName = f"{taskName}_{len(instances)}"
                instances.append(instanceName)
                
                instancePeriodStartTimeVar = self.getIntVar(instanceName+"_period_start_time")

                # introduce solution space where t.o is equal to or larger than 0
                if Config.useOffSet:
                    taskOffsetVar = self.getIntVar(taskName+"_offset")
                    self.prob += instancePeriodStartTimeVar == instancePeriodStartTime + taskOffsetVar
                    self.prob += taskOffsetVar >= 0  # tasks offset must be positive
                    self.prob += taskOffsetVar <= taskPeriod - 1 # tasks can be offset atmost 1 less than period
                else:
                    self.prob += instancePeriodStartTimeVar == instancePeriodStartTime

                # Compute task instance end time
                instancePeriodEndTimeVar = self.getIntVar(instanceName+"_period_end_time")
                self.prob += instancePeriodEndTimeVar == instancePeriodStartTimeVar + taskPeriod
     
                
            
                # Encode the execution bounds of the task instance in LP constraints
                # ------------------------------------------------------------------
                
                # Add to list of unknown integer variables with the instance start and end times
                taskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(instanceName))
                taskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(instanceName))

                # Equation 2a: 𝑡^𝑖.𝑠 = 𝑡.𝑜 + 𝑖 × 𝑡.𝑝 + 𝑡.𝑎
                # 𝑡^𝑖.𝑠, t.o, and t.a are unknowns 
                # t.o and t.a must be greater than or equal to 0
                # Therefore, 𝑡^𝑖.𝑠 >= 𝑖 × 𝑡.𝑝
                self.prob += taskInstStartTimeVar >= instancePeriodStartTimeVar

                # Task execution has to end at or before the period
                # Equation 2c: 𝑡𝑖.𝑒 ≤ 𝑡.𝑜 + (𝑖 + 1) × 𝑡 .𝑝
                self.prob += taskInstEndTimeVar <= instancePeriodEndTimeVar

                #Task execution time has to be greater than or equal to wcet
                # Equation 2b: 𝑡𝑖.𝑒 = 𝑡𝑖.𝑠 + 𝑡.𝛿
                # rearrenage 𝑡.𝛿 = 𝑡𝑖.𝑒 - 𝑡𝑖.𝑠
                # Equation 2d: 𝑡.𝛿 >= 𝑡.wcet
                # subsutite 2b: 𝑡𝑖.𝑒 - 𝑡𝑖.𝑠 >= 𝑡.wcet
                self.prob += taskInstEndTimeVar - taskInstStartTimeVar >= taskWcet
                
                # ------------------------------------------------------------------

                # FIXME: Tailor constraints based on whether each task instance can have its own task parameters
                if not Config.individualLetInstanceParams:
                    # Make sure all LET instances start and end at the same time
                    # Add / Set Task start times
                    taskStartTimeVar = self.getIntVar(self.taskInstStartTime(taskName))
                    taskEndTimeVar = self.getIntVar(self.taskInstEndTime(taskName))

                    # Make sure all LET instances start and end at the same time
                    self.prob += taskInstStartTimeVar - taskStartTimeVar == instancePeriodStartTimeVar
                    # Make sure all LET instances start and end at the same time
                    self.prob += taskInstEndTimeVar - taskEndTimeVar == instancePeriodStartTimeVar


            allTaskInstances[taskName] = instances
        return allTaskInstances
    
    # Equestion 3 for all task instances
    def createTaskExecutionConstraints(self, allTaskInstances, cores):
        self.writeComment("Make sure task executions do not overlap")
        # Add pairwise task constraints to make sure task executions do not overlap (single core)
        while bool(allTaskInstances):
            # Get all instances of all tasks
            # ∀𝑡𝑖𝑥, 𝑡𝑗𝑦 ∈ T𝑆, 𝑥 ≠ 𝑦
            taskName, instances = allTaskInstances.popitem()
            for instance in instances:
                for otherTaskName, otherInstances in allTaskInstances.items():
                    for otherInstance in otherInstances:
                        self.writeTaskOverlapConstraint(instance, otherInstance)

    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst):
        controlVariable = self.getBoolVar("execution_control_"+currentTaskInst+"_"+otherTaskInst)
        currentTaskInstStartTime = self.getIntVar(self.taskInstStartTime(currentTaskInst))
        currentTaskInstEndTime  = self.getIntVar(self.taskInstEndTime(currentTaskInst))
        otherTaskInstStartTime = self.getIntVar(self.taskInstStartTime(otherTaskInst))
        otherTaskInstEndTime  = self.getIntVar(self.taskInstEndTime(otherTaskInst))
        # These two constraints ensure the tasks either execute before OR after one another and not overlap
        # Equation 3a and Equation 3b

        # 𝑡𝑖𝑥.𝑒 − 𝑡𝑗𝑦.𝑠 ≤ N × 𝑏𝑡𝑎𝑠𝑘𝑥,𝑖,𝑦,𝑗
        self.prob += currentTaskInstEndTime - otherTaskInstStartTime <= self.lpLargeConstant * controlVariable

        #𝑡𝑗𝑦.𝑒 − 𝑡𝑖𝑥.𝑠 ≤ N − N × 𝑏𝑡𝑎𝑠𝑘𝑥,𝑖,𝑦,
        self.prob += otherTaskInstEndTime - currentTaskInstStartTime <= self.lpLargeConstant - self.lpLargeConstant * controlVariable
    
    # Equation 4
    # A dependency instance is simply a pair of source and destination task instances
    # Each dependency instance can only have 1 source task but can have mutiple destinations
    # The selected source tasks must complete its execution before the destination task 
    def createTaskDependencyConstraints(self, system, allTaskInstances):
        self.writeComment("Each destination task instance of a dependency can only be connected to one source")

        # Constrain each dependency task instance to only have one source task instance
        # ∀𝑑 ∈ 𝐷
        for dependency in system['DependencyStore']:
            # Dependency parameters
            name = dependency['name']
            srcTask = dependency['source']['task']
            destTask = dependency['destination']['task']
            dependencyPair = f"{dependency['source']['task']}_{dependency['destination']['task']}"

            # Dependencies to the environment are left unconstrained.
            if "__system" in dependencyPair:
                continue

            # Get source and destination task instances
            srcTaskInstances = allTaskInstances[srcTask]
            destTaskInstances = allTaskInstances[destTask]

            self.writeDependencySourceTaskSelectionConstraint(name, dependencyPair, srcTaskInstances, destTaskInstances)

    def writeDependencySourceTaskSelectionConstraint(self, name, taskDependencyPair, srcTaskInstances, destTaskInstances):
        self.writeComment(f"Select source task for each instance of dependency {name}. Calculate dependency delays")
        
        # There can only be one source task for a task dependency instance
        self.dependencyInstanceDelayVariables[taskDependencyPair] = []
        # ∀𝑡𝑗𝑦 ∈ T𝑑.𝑑𝑒𝑠𝑡
        for destInst in destTaskInstances:
            destTaskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(destInst))
            destTaskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(destInst))
            # Iterate over source task instances
            # ∀𝑡𝑖𝑥 ∈ T𝑑.𝑠𝑟𝑐
            srcInstControlVariables = list()
            for srcInst in srcTaskInstances:
                srcTaskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(srcInst))
                srcTaskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(srcInst))
                # Name for task dependency instance and its boolean control variable.
                dependencyInstance = f"{srcInst}_{destInst}"
                dependencyInstanceControlVariable = self.getBoolVar(f"dep_{dependencyInstance}")   

                srcInstControlVariables.append(dependencyInstanceControlVariable)

                # Task dependency is valid only when the source task does not end after the start of the destination task.
                # dependencyInstanceControlVariable is set to 1 if this is the case.
                # Equation 4a: 𝑡𝑖𝑥.𝑒 − 𝑡𝑗𝑦.𝑠 ≤ N − N × 𝑏𝑑𝑒𝑝 𝑥,𝑖,𝑦, 𝑗
                # [ Source Task ]
                #                 [ Dest Task ]
                self.prob += srcTaskInstEndTimeVar - destTaskInstStartTimeVar <= self.lpLargeConstant - self.lpLargeConstant * dependencyInstanceControlVariable 
                
                # Calculate the delay of the dependency instance.
                # Equestion 5
                dependencyInstanceDelayVar = self.getIntVar(f"delay_{dependencyInstance}")
                # Equestion 5a
                self.prob += dependencyInstanceDelayVar >= 0
                # Equestion 5b and 5c
                # if selected then:
                    # end-to-end delay for the dependency must be = to destaskInstEndTimeVar - srcTaskInstStartTimeVar
                    # destaskInstEndTimeVar must be after srcTaskInstStartTimeVar so that the difference is >= 0
                # if not selected then:
                    # it is always larger than a very large negative number i.e., any value >= 0
                    # it is always smaller than a very large number i.e., any value < lpLargeConstant but 0 will be choosen as the objective is to mininise
                self.prob += dependencyInstanceDelayVar >= destTaskInstEndTimeVar - srcTaskInstStartTimeVar - self.lpLargeConstant + self.lpLargeConstant * dependencyInstanceControlVariable  
                # Equestion 5c
                
                self.prob += dependencyInstanceDelayVar <= destTaskInstEndTimeVar - srcTaskInstStartTimeVar + self.lpLargeConstant - self.lpLargeConstant * dependencyInstanceControlVariable 
               
                # Create list of all dependency delay variables
                self.dependencyInstanceDelayVariables[taskDependencyPair].append(dependencyInstanceDelayVar.name)     
    
            # Create the constraint where all possible dependency instances sum to 1, i.e., only one instance is selected
            # Equestion 4b: Σ︁ 𝑏𝑑𝑒𝑝 = 1
            self.prob += pl.lpSum(srcInstControlVariables) == 1


    def writeDelayConstraints(self, delayVariable, delayValue, isTighten):
        if (isTighten):
            self.prob += self.getIntVar(delayVariable) <= delayValue - 1
        else:
            self.prob += self.getIntVar(delayVariable) <= delayValue 
            
    def solve(self, solver):
        self.prob.writeLP(self.filename)
        #self.prob.writeMPS(self.filename+".mps")
        self.prob.solve(solver)
        
        #print(self.prob.variables)
        for v in self.prob.variables():
            print(str(v.name) + " : " + str(v.varValue))


