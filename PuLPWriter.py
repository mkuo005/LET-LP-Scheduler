import pulp as pl
import math
from enum import Enum
class  PuLPWriter:
    equations = [{}]
    OVERALL_END_TO_END = 1
    MIN_SUM_END_TIME = 2

    def listAvalaibleSolvers(self):
        solver_list = pl.listSolvers(onlyAvailable=True)
        print("Avaliable Solver on System:" + solver_list)
        print("Supported Solvers: "+pl.listSolvers())

    def __init__(self, filename, objectiveVariable, lpLargeConstant, objectiveType=OVERALL_END_TO_END):
        self.prob = pl.LpProblem(filename, pl.LpMinimize)
        self.filename = filename
        self.objectiveVariable = pl.LpVariable(objectiveVariable, None, None, pl.LpInteger)
        self.lpLargeConstant = lpLargeConstant
        self.objectiveType = objectiveType
        self.dependencyInstanceDelayVariables = {}
        self.allTaskInstances = {}
        
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
        if (self.objectiveType == self.OVERALL_END_TO_END):
            self.prob += self.objectiveVariable == pl.lpSum([self.getIntVar(x) for v in self.dependencyInstanceDelayVariables.values() for x in v])
        elif (self.objectiveType == self.MIN_SUM_END_TIME):
            self.prob += self.objectiveVariable == pl.lpSum([self.getIntVar(self.taskInstPeriodEndTime(x)) for v in self.allTaskInstances.values() for x in v])
   
    def taskOffset(self, taskInstance):
        return f"{taskInstance}_offset"
    
    def taskInstDelay(self, srcTaskIns, destTaskIns):
        return f"delay_{srcTaskIns}_{destTaskIns}"
    
    def taskInstStartTime(self, taskInstance):
        return f"{taskInstance}_start_time"
    
    def taskInstEndTime(self, taskInstance):
        return f"{taskInstance}_end_time"
    
    def taskInstPeriodStartTime(self, taskInstance):
        return f"{taskInstance}_period_start_time"
    
    def taskInstPeriodEndTime(self, taskInstance):
        return f"{taskInstance}_period_end_time"
    
    def taskInstExecutionControl(self, srcTaskIns, destTaskIns):
        return f"{srcTaskIns}_{destTaskIns}_execution_control"
    
    def depInst(self, srcTaskIns, destTaskIns):
        return f"{srcTaskIns}_{destTaskIns}_dep"
    
    def instLink(self, srcTaskIns, destTaskIns):
        return f"{srcTaskIns}_{destTaskIns}"
    
    def instVarName(self, taskName, insName): 
        return f"{taskName}_{insName}"
    
    def getIntVar(self, name):
        if (name in self.vars) == False:
            lpVar = pl.LpVariable(name, None, None, cat=pl.LpInteger)
            self.vars[name] = lpVar
        return self.vars[name]
    
    def getBoolVar(self, name):
        print(f"line 79: {name}, {self.vars}")
        if (name in self.vars) == False:
            lpVar = pl.LpVariable(name, lowBound=0, upBound=1, cat=pl.LpBinary)
            self.vars[name] = lpVar
            print(f"line 83: {lpVar}, {self.vars[name]}")
        return self.vars[name]
    
    # Equation 2
    # Create constraints to compute task instance start and end times for each task instance (i) within the scheduling window
    def createTaskInstancesAsConstraints(self, system, schedulingWindow, cores, Config):
        allTaskInstances = {}
        for task in system['EntityStore']:
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
                instanceName = self.instVarName(taskName, len(instances))
                instances.append(instanceName)

                instancePeriodStartTimeVar = self.getIntVar(self.taskInstPeriodStartTime(instanceName))

                # introduce solution space where t.o is equal to or larger than 0
                if Config.useOffSet:
                    taskOffsetVar = self.getIntVar(self.taskOffset(taskName))
                    self.prob += instancePeriodStartTimeVar == instancePeriodStartTime + taskOffsetVar
                    self.prob += taskOffsetVar >= 0  # tasks offset must be positive
                    self.prob += taskOffsetVar <= taskPeriod - 1 # tasks can be offset atmost 1 less than period
                else:
                    self.prob += instancePeriodStartTimeVar == instancePeriodStartTime

                # Compute task instance end time
                instancePeriodEndTimeVar = self.getIntVar(self.taskInstPeriodEndTime(instanceName))
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
                if (Config.useHeterogeneousCores):
                    currentTaskAllocations = {}
                    for c in cores:
                        currentTaskCoreAllocationVariable = self.getBoolVar(self.taskInstCoreAllocation(instanceName,c["name"]))
                        currentTaskAllocations[currentTaskCoreAllocationVariable] = math.ceil(taskWcet / float(c["speedup"]))

                    self.prob += taskInstEndTimeVar - taskInstStartTimeVar >= pl.lpSum([alloc * currentTaskAllocations[alloc] for alloc in currentTaskAllocations.keys()]), "WCET_"+instanceName
                else:
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

            
            self.allTaskInstances[taskName] = instances
        return self.allTaskInstances.copy() #maintain the all task instances dictionary for use in different object functions
    
    # Equation 3 for all task instances
    def createTaskExecutionConstraints(self, allTaskInstances, cores, Config):
        print(f"allTaskInstances: {allTaskInstances}")
        print(f"cores: {cores}")
        self.writeComment("Make sure task executions do not overlap")
        for taskInstances in allTaskInstances.values():
            print(f"First for loop taskInstances: {taskInstances}")
            for instance in taskInstances:
                print(f"Second for loop instance: {instance}")
                currentTaskAllocations = list()
                for c in cores:
                    currentTaskCoreAllocationVariable = self.getBoolVar(self.taskInstCoreAllocation(instance,c["name"]))
                    print(f"thrid for loop currndTaskCoreAllocationVariable: {currentTaskCoreAllocationVariable}")
                    currentTaskAllocations.append(currentTaskCoreAllocationVariable)
                # Task instances must only be allocated to a single core
                self.prob += pl.lpSum(currentTaskAllocations) == 1 #only 1 core can be selected
                print(f"currentTaskAllocations: {currentTaskAllocations}")
        if Config.restrictTaskInstancesToSameCore:
            for c in cores:
                for taskName, taskInstances in allTaskInstances.items():
                    taskCoreAllocationVariable = self.getBoolVar(self.taskInstCoreAllocation(taskName,c["name"]))
                    for instance in taskInstances:
                        currentTaskCoreAllocationVariable = self.getBoolVar(self.taskInstCoreAllocation(instance,c["name"]))
                        self.prob += taskCoreAllocationVariable == currentTaskCoreAllocationVariable, "restrict_"+c["name"]+"_"+taskName+"_"+instance
                        print(f"linet 197: {c}, {taskName}, {taskInstances}, {currentTaskAllocations}")
        print(f"line 189: {self.prob}")
        # Add pairwise task constraints to make sure task executions do not overlap (single core)
        while bool(allTaskInstances):
            # Get all instances of all tasks
            # ∀𝑡𝑖𝑥, 𝑡𝑗𝑦 ∈ T𝑆, 𝑥 ≠ 𝑦
            taskName, instances = allTaskInstances.popitem()
            for instance in instances:
                for otherTaskName, otherInstances in allTaskInstances.items():
                    for otherInstance in otherInstances:
                        self.writeTaskOverlapConstraint(instance, otherInstance, cores)

    def taskInstCoreAllocation(self, task, coreName):
        return f"core_{task}_{coreName}"

    def taskInstCorePairsAllocation(self, srcTask, srcCoreName, destTask, destCoreName):
        return f"pair_{srcTask}_{srcCoreName}_{destTask}_{destCoreName}"
    
    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst, cores):
        taskAllocationPairs = list()
        taskAllocationExclusivePairs = list()
        print(f"line 217: {currentTaskInst}, {otherTaskInst}")
        print(f"line 271: {cores}")

        for srcCore in cores:
            for destCore in cores:
                print(f"source & dest core: {srcCore}, {destCore}")
                currentTaskCoreAllocationVariable = self.getBoolVar(self.taskInstCoreAllocation(currentTaskInst,srcCore["name"]))
                otherTaskCoreAllocationVariable = self.getBoolVar(self.taskInstCoreAllocation(otherTaskInst,destCore["name"]))
                print(f"line 222: {currentTaskCoreAllocationVariable}, {otherTaskCoreAllocationVariable}")

                pairTaskCoreAllocationVariable = self.getBoolVar(self.taskInstCorePairsAllocation(currentTaskInst,srcCore["name"],otherTaskInst,destCore["name"]))
                taskAllocationPairs.append(pairTaskCoreAllocationVariable)
                print(f"line 226: {pairTaskCoreAllocationVariable}, {taskAllocationPairs}")

                #if this pair has been allocated naturally the task allocation must also be allocated
                self.prob += pairTaskCoreAllocationVariable <= currentTaskCoreAllocationVariable
                self.prob += pairTaskCoreAllocationVariable <= otherTaskCoreAllocationVariable
                if not (srcCore["name"] == destCore["name"]):
                    taskAllocationExclusivePairs.append(pairTaskCoreAllocationVariable)
        print(f"line 233: {self.prob}")

        # Only 1 pair can be selected
        self.prob += pl.lpSum(taskAllocationPairs) == 1 

        controlVariable = self.getBoolVar(self.taskInstExecutionControl(currentTaskInst,otherTaskInst))
        currentTaskInstStartTime = self.getIntVar(self.taskInstStartTime(currentTaskInst))
        currentTaskInstEndTime  = self.getIntVar(self.taskInstEndTime(currentTaskInst))
        otherTaskInstStartTime = self.getIntVar(self.taskInstStartTime(otherTaskInst))
        otherTaskInstEndTime  = self.getIntVar(self.taskInstEndTime(otherTaskInst))
        # These two constraints ensure the tasks either execute before OR after one another and not overlap
        # Equation 3a and Equation 3b

        # 𝑡𝑖𝑥.𝑒 − 𝑡𝑗𝑦.𝑠 ≤ N × 𝑏𝑡𝑎𝑠𝑘𝑥,𝑖,𝑦,𝑗
        print(f"line 249: {self.lpLargeConstant}")
        self.prob += currentTaskInstEndTime - otherTaskInstStartTime <= self.lpLargeConstant * controlVariable + pl.lpSum([x * self.lpLargeConstant for x in taskAllocationExclusivePairs])
        print(f"line 252: {currentTaskInstEndTime} - {otherTaskInstStartTime} <= {self.lpLargeConstant} * {controlVariable} + {pl.lpSum([x * self.lpLargeConstant for x in taskAllocationExclusivePairs])}")
        print(f"line 253: {taskAllocationExclusivePairs}")

        #𝑡𝑗𝑦.𝑒 − 𝑡𝑖𝑥.𝑠 ≤ N − N × 𝑏𝑡𝑎𝑠𝑘𝑥,𝑖,𝑦,
        self.prob += otherTaskInstEndTime - currentTaskInstStartTime <= self.lpLargeConstant - self.lpLargeConstant * controlVariable + pl.lpSum([x * self.lpLargeConstant for x in taskAllocationExclusivePairs])
    
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
            dependencyPair = self.instLink(dependency['source']['task'],dependency['destination']['task'])

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
           
                dependencyInstanceControlVariable = self.getBoolVar(self.depInst(srcInst, destInst))   

                srcInstControlVariables.append(dependencyInstanceControlVariable)

                # Task dependency is valid only when the source task does not end after the start of the destination task.
                # dependencyInstanceControlVariable is set to 1 if this is the case.
                # Equation 4a: 𝑡𝑖𝑥.𝑒 − 𝑡𝑗𝑦.𝑠 ≤ N − N × 𝑏𝑑𝑒𝑝 𝑥,𝑖,𝑦, 𝑗
                # [ Source Task ]-.
                #                  \
                #                   `->[ Dest Task ]
                self.prob += srcTaskInstEndTimeVar - destTaskInstStartTimeVar <= self.lpLargeConstant - self.lpLargeConstant * dependencyInstanceControlVariable 
                
                # Calculate the delay of the dependency instance.
                # Equation 5
                dependencyInstanceDelayVar = self.getIntVar(self.taskInstDelay(srcInst, destInst))
                # Equation 5a
                self.prob += dependencyInstanceDelayVar >= 0
                # Equations 5b and 5c
                # if selected then:
                    # end-to-end delay for the dependency must be = to destaskInstEndTimeVar - srcTaskInstStartTimeVar
                    # destaskInstEndTimeVar must be after srcTaskInstStartTimeVar so that the difference is >= 0
                # if not selected then:
                    # it is always larger than a very large negative number i.e., any value >= 0
                    # it is always smaller than a very large number i.e., any value < lpLargeConstant but 0 will be choosen as the objective is to mininise
                self.prob += dependencyInstanceDelayVar >= destTaskInstEndTimeVar - srcTaskInstStartTimeVar - self.lpLargeConstant + self.lpLargeConstant * dependencyInstanceControlVariable  
                # Equation 5c
                
                self.prob += dependencyInstanceDelayVar <= destTaskInstEndTimeVar - srcTaskInstStartTimeVar + self.lpLargeConstant - self.lpLargeConstant * dependencyInstanceControlVariable 
               
                # Create list of all dependency delay variables
                self.dependencyInstanceDelayVariables[taskDependencyPair].append(dependencyInstanceDelayVar.name)     
    
            # Create the constraint where all possible dependency instances sum to 1, i.e., only one instance is selected
            # Equation 4b: Σ︁ 𝑏𝑑𝑒𝑝 = 1
            self.prob += pl.lpSum(srcInstControlVariables) == 1


    def writeDelayConstraints(self, delayVariable, delayValue, isTighten):
        if (isTighten):
            self.prob += self.getIntVar(delayVariable) <= delayValue - 1
        else:
            self.prob += self.getIntVar(delayVariable) <= delayValue 
            
    def solve(self, solverName):
        solverDict = {'keepFiles': 0,
                     'mip': True,
                     'msg': True,
                     'options': [],
                     'solver': solverName,
                     'timeLimit': None,
                     'warmStart': False}
        
        #set custom parameters for Gurobi solver
        if solverName == "GUROBI_CMD":
            solverDict['options'] = [("IntegralityFocus","1")] #make solution harder but tries to ensure integer results, some pc was not producing exact results for decision variables
        solver = pl.getSolverFromDict(solverDict)
        self.prob.writeLP(self.filename)
        #self.prob.writeMPS(self.filename+".mps")
        self.prob.solve(solver)
        
        #print(self.prob.variables)
        for v in self.prob.variables():
            print(str(v.name) + " : " + str(v.varValue))


