class LpSolveLPWriter:
    def __init__(self, filename, objectiveVariable, lpLargeConstant):
        self.filename = filename
        self.file = open(filename, "w")
        self.objectiveVariable = objectiveVariable
        self.lpLargeConstant = lpLargeConstant
        
        self.dependencyTaskTable = {}
        self.dependencyDelaysSum = ""
        self.dependencyConstraints = ""

        # All Boolean and integer variables used
        self.booleanVariables = []
        self.intVariables = []

    def write(self, string):
        self.file.write(string)

    def writeObjective(self):
        self.file.write(f"min: {self.objectiveVariable};\n")

    def writeObjectiveEquation(self):
        self.file.write(f"{self.objectiveVariable} = {self.dependencyDelaysSum};\n")

    def writeComment(self, string):
        self.file.write(f"\n/* {string} */\n")

    def taskInstStartTime(self, taskInstance):
        return f"U{taskInstance}_start_time"
    
    def taskInstEndTime(self, taskInstance):
        return f"U{taskInstance}_end_time"

    # FIXME: Tailor constraints based on whether each task instance can have its own task parameters
    def writeTaskInstanceExecutionBounds(self, taskName, taskInstance, instanceStartTime, instanceEndTime, wcet, sameLETForAllInstances):
        # Add to list of unknown integer variables with the instance start and end times
        self.intVariables.append(self.taskInstStartTime(taskInstance))
        self.intVariables.append(self.taskInstEndTime(taskInstance))
        
        # Task execution has to start at or after the period
        self.file.write(f"{self.taskInstStartTime(taskInstance)} >= {instanceStartTime};\n")
        
        # Task execution has to end at or before the period
        self.file.write(f"{self.taskInstEndTime(taskInstance)} <= {instanceEndTime};\n")

        # Task execution time has to be greater than or equal to wcet
        self.file.write(f"{self.taskInstEndTime(taskInstance)} - {self.taskInstStartTime(taskInstance)} >= {wcet};\n")
        
        if sameLETForAllInstances:
            # Make sure all LET instances start and end at the same time
            self.file.write(f"{self.taskInstStartTime(taskName)} = {self.taskInstStartTime(taskInstance)} - {instanceStartTime};\n")
            self.file.write(f"{self.taskInstEndTime(taskName)} = {self.taskInstEndTime(taskInstance)} - {instanceStartTime};\n")

    def writeTaskOverlapConstraint(self, currentTaskInst, otherTaskInst):
        controlVariable = "control"+currentTaskInst+"_"+otherTaskInst
        self.booleanVariables.append(controlVariable)

        #These two constraints ensure the tasks either execute before OR after one another and not overlap
        #inst_end_time - other_start_time <= XXXXX * control
        #other_end_time - inst_start_time <= XXXXX - XXXXX * control
        self.file.write(self.taskInstEndTime(currentTaskInst)+ " - " + self.taskInstStartTime(otherTaskInst) +" <= "+str(self.lpLargeConstant) + " " + controlVariable + ";\n")
        self.file.write(self.taskInstEndTime(otherTaskInst)+" - " + self.taskInstStartTime(currentTaskInst) +" <= "+str(self.lpLargeConstant) + " - " + str(self.lpLargeConstant ) + " " + controlVariable + ";\n")

    def writeTaskDependencyConstraint(self, srcTask, destTask, destTaskInstances, srcTaskInstances):
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
                                
                #instance connection is only vaild if the source task finsihes before the destination task start time or else it must be zero
                #The constaint should be 1 when the start_time is larger than the end_time therefore a -ve value or 0
                self.file.write(self.taskInstEndTime(srcInst) + " - " + self.taskInstStartTime(destInst) + " <= " + str(self.lpLargeConstant) + " - " +str(self.lpLargeConstant) +" "+ instanceConnectionControl +";\n")
                
                #append this dependency end-to-end time to total end-to-end time of the system
                if (len(self.dependencyDelaysSum) > 0):
                    self.dependencyDelaysSum += " + "

                self.dependencyConstraints += "EtoE_"+ endToEndConstraintID + " >= 0;\n"
                X = self.taskInstEndTime(destInst) + " - " + self.taskInstStartTime(srcInst)
                self.dependencyConstraints += X +" - "+str(self.lpLargeConstant)+" + "+str(self.lpLargeConstant)+" " +instanceConnectionControl + " <= " + "EtoE_"+ endToEndConstraintID +";\n"
                self.dependencyConstraints += "EtoE_"+ endToEndConstraintID + " <= "+X+" + "+str(self.lpLargeConstant)+" - "+str(self.lpLargeConstant)+" " +instanceConnectionControl +";\n"
                                
                #a simple sum of the difference will be optimising the average - need to think...
                self.dependencyDelaysSum += "EtoE_"+ endToEndConstraintID
                taskDependencyPair = srcTask+"_"+destTask
                self.dependencyTaskTable[taskDependencyPair].append("EtoE_"+ endToEndConstraintID)     
                                
            #There can only be one source
            self.file.write(srcInstString+" = 1;\n")

    def writeBooleanConstraints(self):
        for b in self.booleanVariables:
            self.file.write("bin "+ b + ";\n")
        

    def close(self):
        self.file.close()
