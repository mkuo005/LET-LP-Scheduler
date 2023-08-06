class GurobiLPWriter:
    def __init__(self, filename, objectiveVariable, lpLargeConstant):
        self.filename = filename
        self.file = open(filename, "w")
        self.objectiveVariable = objectiveVariable
        self.lpLargeConstant = lpLargeConstant
        
        self.dependencyTaskTable = {}
        self.dependencyDelaysSum = ""
        self.dependencyDelayConstraints = ""
        
        #list of all boolean variables used
        self.booleanVariables = []
        #list of all integer variables used
        self.intVariables = []

    def write(self, string):
        self.file.write(string)

    def writeObjective(self):
        self.write(f"Minimize\n{self.objectiveVariable}\n")
        self.write("Subject To\n")

    def writeObjectiveEquation(self):
        self.writeComment("Objective equation")
        self.write(f"{self.objectiveVariable} {self.dependencyDelaysSum} = 0;\n")

    def writeComment(self, string):
        None

    def taskInstStartTime(self, taskInstance):
        return f"U{taskInstance}_start_time"
    
    def taskInstEndTime(self, taskInstance):
        return f"U{taskInstance}_end_time"

    # FIXME: Tailor constraints based on whether each task instance can have its own task parameters
    def writeTaskInstanceExecutionBounds(self, taskName, taskInstance, instanceStartTime, instanceEndTime, wcet, individualLetInstanceParams):
        # Add to list of unknown integer variables with the instance start and end times
        self.intVariables.append(self.taskInstStartTime(taskInstance))
        self.intVariables.append(self.taskInstEndTime(taskInstance))

        # Task execution has to start at or after the period
        self.write(f"{self.taskInstStartTime(taskInstance)} >= {instanceStartTime};\n")
        
        # Task execution has to end at or before the period
        self.write(f"{self.taskInstEndTime(taskInstance)} <= {instanceEndTime};\n")

        # Task execution time has to be greater than or equal to wcet
        sel.write(f"{self.taskInstEndTime(taskInstance)} - {self.taskInstStartTime(taskInstance)} >= {wcet};\n")

        if not individualLetInstanceParams:
            #Make sure all LET instances start and end at the same time
            self.write(self.taskInstStartTime(taskInstance) + " - "+ self.taskInstStartTime(taskName) + " = " + str(instanceStartTime) + ";\n")
            self.write(self.taskInstEndTime(taskInstance) + " - "+ self.taskInstEndTime(taskName) + " = " + str(instanceStartTime) + ";\n")

    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst):
        controlVariable = "control"+currentTaskInst+"_"+otherTaskInst
        self.booleanVariables.append(controlVariable)

        #These two constraints ensure the tasks either execute before OR after one another and not overlap
        #inst_end_time - other_start_time <= XXXXX * control
        #other_end_time - inst_start_time <= XXXXX - XXXXX * control
        self.write(self.taskInstEndTime(currentTaskInst)+ " - " + self.taskInstStartTime(otherTaskInst)   + " - " + str(self.lpLargeConstant) + " " + controlVariable + " <= 0" + "\n")
        self.write(self.taskInstEndTime(otherTaskInst)  + " - " + self.taskInstStartTime(currentTaskInst) + " + " + str(self.lpLargeConstant) + " " + controlVariable + " <= "+str(self.lpLargeConstant)  + "\n")

    def writeDependencySourceTaskSelectionConstraint(self, name, srcTask, srcTaskInstances, destTask, destTaskInstances):
        self.writeComment(f"Dependency {name}")

        taskDependencyPair = srcTask+"_"+destTask
        self.dependencyTaskTable[taskDependencyPair] = []

        for destInst in destTaskInstances:
            srcInstString = ""
            first = True

            #Iterate over source task instances
            for srcInst in srcTaskInstances:
                #instances
                endToEndConstraintID = srcInst+"_"+destInst
                #instance control variable
                instanceConnectionControl = "DEP_"+endToEndConstraintID
                self.booleanVariables.append(instanceConnectionControl)
                #Create the constraint where all the destination instance to source pairs possible are summed and should equal 1 i.e., only one pair is selected
                if (first):
                    srcInstString += instanceConnectionControl
                    first = False
                else:
                    srcInstString += " + " + instanceConnectionControl
                                
                # instance connection is only vaild if the source task finsihes before the destination task start time or else it must be zero
                # The constraint should be 1 when the start_time is larger than the end_time therefore a -ve value or 0
                self.write(self.taskInstEndTime(srcInst) + " - " + self.taskInstStartTime(destInst) + " + " +str(self.lpLargeConstant) +" "+ instanceConnectionControl + " <= " + str(self.lpLargeConstant) + "\n")
                
                # Add this task dependency delay to the sum of all dependency delays
                self.dependencyDelaysSum += " - "

                self.dependencyDelayConstraints += "EtoE_"+ endToEndConstraintID + " >= 0\n"
                X = self.taskInstEndTime(destInst) + " - " + self.taskInstStartTime(srcInst)
                self.dependencyDelayConstraints += X +" + "+str(self.lpLargeConstant)+" " +instanceConnectionControl + " - " + "EtoE_"+ endToEndConstraintID + " <= " + str(self.lpLargeConstant)  +"\n"
                self.dependencyDelayConstraints += X +" - "+str(self.lpLargeConstant)+" " +instanceConnectionControl + " - " + "EtoE_"+ endToEndConstraintID + " >= " +" -"+str(self.lpLargeConstant) +"\n"
                                
                #a simple sum of the difference will be optimising the average - need to think...
                self.dependencyDelaysSum += "EtoE_"+ endToEndConstraintID
                self.dependencyTaskTable[taskDependencyPair].append("EtoE_"+ endToEndConstraintID)     
                                
            #There can only be one source
            self.write(srcInstString+" = 1\n")

    def writeBooleanConstraints(self):
        self.writeComment("Boolean variables")
        self.write("Bounds\n")
        binaries = ""
        for b in self.booleanVariables:
            binaries = binaries + b + " "
        self.write("binary "+ binaries+"\n")
        
    def writeIntegerConstraints(self):
        self.writeComment("Integer variables")
        pass

    def close(self):
        self.file.close()
