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
    def encodeTaskInstances(self, system, schedulingWindow, Config):
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
                
                instancePeriodStartTimeVar = self.getIntVar("Period_Start_"+instanceName)

                # introduce solution spacce where t.o is equal to or larger than 0
                if Config.useOffSet:
                    taskOffsetVar = self.getIntVar("OFFSET_"+taskName)
                    self.prob += instancePeriodStartTimeVar == instancePeriodStartTime + taskOffsetVar
                    self.prob += taskOffsetVar >= 0  # tasks offset must be positive
                    self.prob += taskOffsetVar <= taskPeriod - 1 # tasks can be offset atmost 1 less than period
                else:
                    self.prob += instancePeriodStartTimeVar == instancePeriodStartTime

                # Compute task instance end time
                instancePeriodEndTimeVar = self.getIntVar("Period_End_"+instanceName)
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
    

    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst):
        controlVariable = self.getBoolVar("EXE_"+currentTaskInst+"_"+otherTaskInst)
        currentTaskInstStartTime = self.getIntVar(self.taskInstStartTime(currentTaskInst))
        currentTaskInstEndTime  = self.getIntVar(self.taskInstEndTime(currentTaskInst))
        otherTaskInstStartTime = self.getIntVar(self.taskInstStartTime(otherTaskInst))
        otherTaskInstEndTime  = self.getIntVar(self.taskInstEndTime(otherTaskInst))
        #These two constraints ensure the tasks either execute before OR after one another and not overlap
        #inst_end_time - other_start_time <= XXXXX * control
        #other_end_time - inst_start_time <= XXXXX - XXXXX * control
        self.prob += currentTaskInstEndTime - otherTaskInstStartTime - self.lpLargeConstant * controlVariable <= 0#, "inst_end_time - other_start_time <= XXXXX * control"
        self.prob += otherTaskInstEndTime - currentTaskInstStartTime + self.lpLargeConstant * controlVariable <= self.lpLargeConstant#, "other_end_time - inst_start_time <= XXXXX - XXXXX * control"
    
    def writeDependencySourceTaskSelectionConstraint(self, name, taskDependencyPair, srcTaskInstances, destTaskInstances):
        self.writeComment(f"Select source task for each instance of dependency {name}. Calculate dependency delays")
        
        # There can only be one source task for a task dependency instance
        self.dependencyInstanceDelayVariables[taskDependencyPair] = []
        for destInst in destTaskInstances:
            destTaskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(destInst))
            destaskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(destInst))
            # Iterate over source task instances
            srcInstControlVariables = list()
            for srcInst in srcTaskInstances:
                srcTaskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(srcInst))
                srcTaskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(srcInst))
                # Name for task dependency instance and its boolean control variable.
                dependencyInstance = f"{srcInst}_{destInst}"
                dependencyInstanceControlVariable = self.getBoolVar(f"DEP_{dependencyInstance}")   

                srcInstControlVariables.append(dependencyInstanceControlVariable)

                # Task dependency is valid only when the source task does not end after the start of the destination task.
                # dependencyInstanceControlVariable is set to 1 if this is the case.
                self.prob += srcTaskInstEndTimeVar - destTaskInstStartTimeVar + self.lpLargeConstant * dependencyInstanceControlVariable <= self.lpLargeConstant
                
                # Calculate the delay of the dependency instance.
                delay = destaskInstEndTimeVar - srcTaskInstStartTimeVar
                dependencyInstanceVar = self.getIntVar(f"DELAY_{dependencyInstance}")
                self.prob += dependencyInstanceVar >= 0
                self.prob += delay + self.lpLargeConstant * dependencyInstanceControlVariable - dependencyInstanceVar <= self.lpLargeConstant
                self.prob += delay - self.lpLargeConstant * dependencyInstanceControlVariable - dependencyInstanceVar <= self.lpLargeConstant
                                
                self.dependencyInstanceDelayVariables[taskDependencyPair].append(dependencyInstanceVar.name)     
    
            # Create the constraint where all possible dependency instances sum to 1, i.e., only one instance is selected
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


