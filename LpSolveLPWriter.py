class LpSolveLPWriter:
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
        self.write(f"min: {self.objectiveVariable};\n")

    def writeObjectiveEquation(self):
        self.writeComment("Objective equation")
        dependencyInstanceDelays = ' + '.join([x for v in self.dependencyInstanceDelayVariables.values() for x in v])
        self.write(f"{self.objectiveVariable} = {dependencyInstanceDelays};\n")

    def writeComment(self, string):
        self.write(f"\n/* {string} */\n")

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
        self.write(f"{self.taskInstStartTime(taskInstance)} >= {instanceStartTime};\n")
        
        # Task execution has to end at or before the period
        self.write(f"{self.taskInstEndTime(taskInstance)} <= {instanceEndTime};\n")

        # Task execution time has to be greater than or equal to wcet
        self.write(f"{self.taskInstEndTime(taskInstance)} - {self.taskInstStartTime(taskInstance)} >= {wcet};\n")
        
        if not individualLetInstanceParams:
            # Make sure all LET instances start and end at the same time
            self.write(f"{self.taskInstStartTime(taskName)} = {self.taskInstStartTime(taskInstance)} - {instanceStartTime};\n")
            self.write(f"{self.taskInstEndTime(taskName)} = {self.taskInstEndTime(taskInstance)} - {instanceStartTime};\n")

    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst, cores):
        controlVariables = []
        for core in cores:
            coreName = core["name"]
            controlVariable = f"EXE_{currentTaskInst}_{otherTaskInst}_{coreName}"
            self.booleanVariables.add(controlVariable)
            controlVariables.append(controlVariable)

        # These two constraints ensure the tasks either execute before OR after one another and not overlap
        # inst_end_time - other_start_time <= XXXXX * control
        # other_end_time - inst_start_time <= XXXXX - XXXXX * control
        self.write(f"{self.taskInstEndTime(currentTaskInst)} - {self.taskInstStartTime(otherTaskInst)} <= {self.lpLargeConstant} {controlVariable};\n") #Need to think about only enable constraint if they are on the same core
        self.write(f"{self.taskInstEndTime(otherTaskInst)} - {self.taskInstStartTime(currentTaskInst)} <= {self.lpLargeConstant} - {self.lpLargeConstant} {controlVariable};\n")

    def writeDependencySourceTaskSelectionConstraint(self, name, taskDependencyPair, srcTaskInstances, destTaskInstances):
        self.writeComment(f"Select source task for each instance of dependency {name}. Calculate dependency delays")

        # There can only be one source task for a task dependency instance
        self.dependencyInstanceDelayVariables[taskDependencyPair] = []
        for destInst in destTaskInstances:
            # Iterate over source task instances
            srcInstControlVariables = set()
            srcInstSelectionString = ""
            dependencyDelayConstraintsString = ""
            for srcInst in srcTaskInstances:
                # Name for task dependency instance and its boolean control variable.
                dependencyInstance = f"{srcInst}_{destInst}"
                dependencyInstanceControlVariable = f"DEP_{dependencyInstance}"
                self.booleanVariables.add(dependencyInstanceControlVariable)
                srcInstControlVariables.add(dependencyInstanceControlVariable)
                                
                # Task dependency is valid only when the source task does not end after the start of the destination task.
                # dependencyInstanceControlVariable is set to 1 if this is the case.
                srcInstSelectionString += f"{self.taskInstEndTime(srcInst)} - {self.taskInstStartTime(destInst)} <= {self.lpLargeConstant} - {self.lpLargeConstant} {dependencyInstanceControlVariable};\n"

                # Calculate the delay of the dependency instance.
                delay = f"{self.taskInstEndTime(destInst)} - {self.taskInstStartTime(srcInst)}"
                dependencyDelayConstraintsString += f"DELAY_{dependencyInstance} >= 0;\n"
                dependencyDelayConstraintsString += f"{delay} - {self.lpLargeConstant} + {self.lpLargeConstant} {dependencyInstanceControlVariable} <= DELAY_{dependencyInstance};\n"
                dependencyDelayConstraintsString += f"DELAY_{dependencyInstance} <= {delay} + {self.lpLargeConstant} - {self.lpLargeConstant} {dependencyInstanceControlVariable};\n"
                
                self.dependencyInstanceDelayVariables[taskDependencyPair].append(f"DELAY_{dependencyInstance}")     
                                
            self.write(srcInstSelectionString)

            # Create the constraint where all possible dependency instances sum to 1, i.e., only one instance is selected
            self.write(f"{' + '.join(srcInstControlVariables)} = 1;\n")
            
            self.write(f"{dependencyDelayConstraintsString}\n")

    def writeBooleanConstraints(self):
        self.writeComment("Boolean variables")
        for bool in self.booleanVariables:
            self.write(f"bin {bool};\n")

    def writeIntegerConstraints(self):
        self.writeComment("Integer variables")
        for int in self.intVariables:
            self.write(f"int {int};\n")

    def close(self):
        self.file.close()
