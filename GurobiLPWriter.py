class GurobiLPWriter:
    def __init__(self, filename, objectiveVariable, lpLargeConstant):
        self.filename = filename
        self.file = open(filename, "w")
        self.objectiveVariable = objectiveVariable
        self.lpLargeConstant = lpLargeConstant
        
        self.dependencyInstanceDelayVariables = {}
        
        # All Boolean and integer variables used
        self.booleanVariables = set()
        self.intVariables = set()

    def write(self, string):
        self.file.write(string)

    def writeObjective(self):
        self.write(f"Minimize\n{self.objectiveVariable}\nSubject To\n")

    def writeObjectiveEquation(self):
        self.writeComment("Objective equation")
        dependencyInstanceDelays = ' - '.join([x for v in self.dependencyInstanceDelayVariables.values() for x in v])
        self.write(f"{self.objectiveVariable} - {dependencyInstanceDelays} = 0;\n")

    def writeComment(self, string):
        None

    def taskInstStartTime(self, taskInstance):
        return f"U{taskInstance}_start_time"
    
    def taskInstEndTime(self, taskInstance):
        return f"U{taskInstance}_end_time"

    # FIXME: Tailor constraints based on whether each task instance can have its own task parameters
    def writeTaskInstanceExecutionBounds(self, taskName, taskInstance, instanceStartTime, instanceEndTime, wcet, individualLetInstanceParams):
        # Add to list of unknown integer variables with the instance start and end times
        self.intVariables.add(self.taskInstStartTime(taskInstance))
        self.intVariables.add(self.taskInstEndTime(taskInstance))

        # Task execution has to start at or after the period
        self.write(f"{self.taskInstStartTime(taskInstance)} >= {instanceStartTime}\n")
        
        # Task execution has to end at or before the period
        self.write(f"{self.taskInstEndTime(taskInstance)} <= {instanceEndTime}\n")

        # Task execution time has to be greater than or equal to wcet
        self.write(f"{self.taskInstEndTime(taskInstance)} - {self.taskInstStartTime(taskInstance)} >= {wcet}\n")

        if not individualLetInstanceParams:
            #Make sure all LET instances start and end at the same time
            self.write(self.taskInstStartTime(taskInstance) + " - "+ self.taskInstStartTime(taskName) + " = " + str(instanceStartTime) + ";\n")
            self.write(self.taskInstEndTime(taskInstance) + " - "+ self.taskInstEndTime(taskName) + " = " + str(instanceStartTime) + ";\n")

    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst, cores): #to fix add multicore support
        controlVariable = "EXE_"+currentTaskInst+"_"+otherTaskInst
        self.booleanVariables.add(controlVariable)

        #These two constraints ensure the tasks either execute before OR after one another and not overlap
        #inst_end_time - other_start_time <= XXXXX * control
        #other_end_time - inst_start_time <= XXXXX - XXXXX * control
        self.write(self.taskInstEndTime(currentTaskInst)+ " - " + self.taskInstStartTime(otherTaskInst)   + " - " + str(self.lpLargeConstant) + " " + controlVariable + " <= 0" + "\n")
        self.write(self.taskInstEndTime(otherTaskInst)  + " - " + self.taskInstStartTime(currentTaskInst) + " + " + str(self.lpLargeConstant) + " " + controlVariable + " <= "+str(self.lpLargeConstant)  + "\n")

    def writeDependencySourceTaskSelectionConstraint(self, name, taskDependencyPair, srcTaskInstances, destTaskInstances):
        self.writeComment(f"Select source task for each instance of dependency {name}. Calculate dependency delays")
        
        # There can only be one source task for a task dependency instance
        self.dependencyInstanceDelayVariables[taskDependencyPair] = []
        for destInst in destTaskInstances:
            # Iterate over source task instances
            srcInstControlVariables = list()
            srcInstSelectionString = ""
            dependencyDelayConstraintsString = ""
            for srcInst in srcTaskInstances:
                # Name for task dependency instance and its boolean control variable.
                dependencyInstance = f"{srcInst}_{destInst}"
                dependencyInstanceControlVariable = f"DEP_{dependencyInstance}"
                self.booleanVariables.add(dependencyInstanceControlVariable)
                srcInstControlVariables.append(dependencyInstanceControlVariable)

                # Task dependency is valid only when the source task does not end after the start of the destination task.
                # dependencyInstanceControlVariable is set to 1 if this is the case.
                srcInstSelectionString += f"{self.taskInstEndTime(srcInst)} - {self.taskInstStartTime(destInst)} + {self.lpLargeConstant} {dependencyInstanceControlVariable} <= {self.lpLargeConstant}\n"

                # Calculate the delay of the dependency instance.
                delay = f"{self.taskInstEndTime(destInst)} - {self.taskInstStartTime(srcInst)}"
                dependencyDelayConstraintsString += f"DELAY_{dependencyInstance} >= 0\n"
                dependencyDelayConstraintsString += f"{delay} + {self.lpLargeConstant} {dependencyInstanceControlVariable} - DELAY_{dependencyInstance} <= {self.lpLargeConstant}\n"
                dependencyDelayConstraintsString += f"{delay} - {self.lpLargeConstant} {dependencyInstanceControlVariable} - DELAY_{dependencyInstance} >= -{self.lpLargeConstant}\n"
                                
                self.dependencyInstanceDelayVariables[taskDependencyPair].append("DELAY_"+ dependencyInstance)     

            self.write(srcInstSelectionString)   
                                
            # Create the constraint where all possible dependency instances sum to 1, i.e., only one instance is selected
            self.write(f"{' + '.join(srcInstControlVariables)} = 1\n")

            self.write(f"{dependencyDelayConstraintsString}\n")

    def writeBooleanConstraints(self):
        self.writeComment("Boolean variables")
        self.write("Bounds\n")
        self.write(f"binary {' '.join(self.booleanVariables)}\n")

    def writeIntegerConstraints(self):
        self.writeComment("Integer variables")
        #
        pass

    def close(self):
        self.file.close()
