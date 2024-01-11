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

    # FIXME: Tailor constraints based on whether each task instance can have its own task parameters
    def writeTaskInstanceExecutionBounds(self, taskName, taskInstance, instanceStartTime, instanceEndTime, wcet, individualLetInstanceParams):
        # Add to list of unknown integer variables with the instance start and end times
        taskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(taskInstance))
        taskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(taskInstance))

        self.prob += taskInstStartTimeVar >= instanceStartTime#, "Task execution has to start at or after the period"
        self.prob += taskInstEndTimeVar <= instanceEndTime#, "Task execution has to end at or before the period"
        self.prob += taskInstEndTimeVar - taskInstStartTimeVar >= wcet#, "Task execution time has to be greater than or equal to wcet"

        if not individualLetInstanceParams:
            # Make sure all LET instances start and end at the same time
            # Add / Set Task start times
            taskStartTimeVar = self.getIntVar(self.taskInstStartTime(taskName))
            taskEndTimeVar = self.getIntVar(self.taskInstEndTime(taskName))
            self.prob += taskInstStartTimeVar - taskStartTimeVar == instanceStartTime#, "Make sure all LET instances start and end at the same time"
            self.prob += taskInstEndTimeVar - taskEndTimeVar == instanceStartTime#, "Make sure all LET instances start and end at the same time"

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
            srcInstSelectionString = ""
            dependencyDelayConstraintsString = ""
            for srcInst in srcTaskInstances:
                srcTaskInstStartTimeVar = self.getIntVar(self.taskInstStartTime(srcInst))
                srcTaskInstEndTimeVar = self.getIntVar(self.taskInstEndTime(srcInst))
                # Name for task dependency instance and its boolean control variable.
                dependencyInstance = f"{srcInst}_{destInst}"
                dependencyInstanceControlVariable = self.getBoolVar(f"DEP_{dependencyInstance}")   

                srcInstControlVariables.append(dependencyInstanceControlVariable)

                # Task dependency is valid only when the source task does not end after the start of the destination task.
                # dependencyInstanceControlVariable is set to 1 if this is the case.
                #srcInstSelectionString += f"{self.taskInstEndTime(srcInst)} - {self.taskInstStartTime(destInst)} + {self.lpLargeConstant} {dependencyInstanceControlVariable} <= {self.lpLargeConstant}\n"
                self.prob += srcTaskInstEndTimeVar - destTaskInstStartTimeVar + self.lpLargeConstant * dependencyInstanceControlVariable <= self.lpLargeConstant
                
                # Calculate the delay of the dependency instance.
                delay = destaskInstEndTimeVar - srcTaskInstStartTimeVar
                dependencyInstanceVar = self.getIntVar(f"DELAY_{dependencyInstance}")
                self.prob += dependencyInstanceVar >= 0
                self.prob += delay + self.lpLargeConstant * dependencyInstanceControlVariable - dependencyInstanceVar <= self.lpLargeConstant
                self.prob += delay - self.lpLargeConstant * dependencyInstanceControlVariable - dependencyInstanceVar <= self.lpLargeConstant
                                
                self.dependencyInstanceDelayVariables[taskDependencyPair].append(dependencyInstanceVar.name)     
    
            # Create the constraint where all possible dependency instances sum to 1, i.e., only one instance is selected
            # self.write(f"{' + '.join(srcInstControlVariables)} = 1\n")
            self.prob += pl.lpSum(srcInstControlVariables) == 1

            # self.write(f"{dependencyDelayConstraintsString}\n")

    def solve(self):
        self.prob.writeLP(self.filename)
        self.prob.solve(pl.GUROBI())


