class LPWriter:
    def __init__(self, filename, veryLargeNumber):
        self.filename = filename
        self.file = open(filename, "w")
        #list of all boolean variables used
        self.booleanVariables = []
        #list of all integer variables used
        self.intVaraibles = []
        self.veryLargeNumber = veryLargeNumber
        self.endToEndTaskTable = {}
        self.endToEndTimeSummation = ""
        self.endToEndConstraints = ""

    def write(self, string):
        self.file.write(string)

    def writeObjective(self, objectiveVariable):
        self.file.write("min: "+objectiveVariable+";\n")

    def writeObjectiveEquation(self):
        self.file.write("endToEndTime = "+self.endToEndTimeSummation+";\n")

    def writeComment(self, string):
        self.file.write("\n/*"+string+"*/\n")

    def taskInstStartTime(self, taskInstance):
        return "U"+taskInstance + "_start_time"
    
    def taskInstEndTime(self, taskInstance):
        return "U"+taskInstance + "_end_time"

    def writeTaskInstanceExecutionBounds(self, taskName, taskInstance, instanceStartTime, instanceDeadline, wcet):
        #task have to start after the period
        self.file.write(self.taskInstStartTime(taskInstance) + " >= "+ str(instanceStartTime) + ";\n")
        #task have to end before the period
        self.file.write(self.taskInstEndTime(taskInstance) + " <= "+ str(instanceDeadline) + ";\n")

        #task execution time need to be larger or equal to wcet
        #Instance end time minus start time must be larger than wcet
        self.file.write(self.taskInstEndTime(taskInstance) + " - "+ self.taskInstStartTime(taskInstance) + " >= " + str(wcet) + ";\n")

        #Make sure all LET instances start and end at the same time
        self.file.write(self.taskInstStartTime(taskName) + " = "+ self.taskInstStartTime(taskInstance) + " - " + str(instanceStartTime) + ";\n")
        self.file.write(self.taskInstEndTime(taskName) + " = "+ self.taskInstEndTime(taskInstance) + " - " + str(instanceStartTime) + ";\n")

    def writeTaskOverlapContraint(self, currentTaskInst, otherTaskInst):
        controlVariable = "control"+currentTaskInst+"_"+otherTaskInst
        self.booleanVariables.append(controlVariable)

        #These two constraints ensure the tasks either execute before OR after one another and not overlap
        #inst_end_time - other_start_time <= XXXXX * control
        #other_end_time - inst_start_time <= XXXXX - XXXXX * control
        self.file.write(self.taskInstEndTime(currentTaskInst)+ " - " + self.taskInstStartTime(otherTaskInst) +" <= "+str(self.veryLargeNumber) + " " + controlVariable + ";\n")
        self.file.write(self.taskInstEndTime(otherTaskInst)+" - " + self.taskInstStartTime(currentTaskInst) +" <= "+str(self.veryLargeNumber) + " - " + str(self.veryLargeNumber ) + " " + controlVariable + ";\n")

    def writeTaskDependencyContraint(self, srcTask, destTask, destTaskInstances, srcTaskInstances):
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
                self.file.write(self.taskInstEndTime(srcInst) + " - " + self.taskInstStartTime(destInst) + " <= " + str(self.veryLargeNumber) + " - " +str(self.veryLargeNumber) +" "+ instanceConnectionControl +";\n")
                
                #append this dependency end-to-end time to total end-to-end time of the system
                if (len(self.endToEndTimeSummation) > 0):
                    self.endToEndTimeSummation += " + "

                self.endToEndConstraints += "EtoE_"+ endToEndConstraintID + " >= 0;\n"
                X = self.taskInstEndTime(destInst) + " - " + self.taskInstStartTime(srcInst)
                self.endToEndConstraints += X +" - "+str(self.veryLargeNumber)+" + "+str(self.veryLargeNumber)+" " +instanceConnectionControl + " <= " + "EtoE_"+ endToEndConstraintID +";\n"
                self.endToEndConstraints += "EtoE_"+ endToEndConstraintID + " <= "+X+" + "+str(self.veryLargeNumber)+" - "+str(self.veryLargeNumber)+" " +instanceConnectionControl +";\n"
                                
                #a simple sum of the difference will be optimising the average - need to think...
                self.endToEndTimeSummation += "EtoE_"+ endToEndConstraintID
                taskDependencyPair = srcTask+"_"+destTask
                self.endToEndTaskTable[taskDependencyPair].append("EtoE_"+ endToEndConstraintID)     
                                
            #There can only be one source
            self.file.write(srcInstString+" = 1;\n")

    def writeBooleanConstraints(self):
        for b in self.booleanVariables:
            self.file.write("bin "+ b + ";\n")
        

    def close(self):
        self.file.close()