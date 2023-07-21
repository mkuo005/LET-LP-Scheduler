#Webserver API
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer # python3
import socketserver 
import time
import argparse
import json
import math
import subprocess
import re
from LPWriter import LPWriter
from GurobiLPWriter import GurobiLPWriter
gurobi = True
sameLETForAllInstances = True
#Webserver to handle requests from LetSyncrhonise
class server(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        #Allow cross origin requests
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
    def end_headers (self):
        self.send_header('Access-Control-Allow-Origin', '*')
        BaseHTTPRequestHandler.end_headers(self)
        
    def _set_headers(self):
        self.send_response(200)
        #self.send_header('Content-type', 'text/html')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
    def _set_error_headers(self):
        self.send_response(501)
        self.send_header('Content-type', 'text/html')

        self.end_headers()
    def do_GET(self):
        self._set_headers()
        self.wfile.write("received get request")
        
    def do_POST(self):
        '''Reads post request body'''
        #self._set_headers()
        content_len = int(self.headers.get('content-length'))
        post_body = self.rfile.read(content_len)
        #print(post_body)
        system = json.loads(post_body.decode("utf-8"))
        schedule = lpScheduler(system)
        if (schedule == None):
            #self.send_response(501, "Scheduler does not support LET parameters")
            self._set_error_headers()
        else:
            self._set_headers()
            self.wfile.write(bytes(json.dumps(schedule),"utf-8"))

    def do_PUT(self):
        self.do_POST();



#LP Scheduler
def lpScheduler(system):
    
    #Current Schedule
    schedule = {
        "DependencyInstancesStore" : [], 
        "EventChainInstanceStore" : [],
        "TaskInstancesStore" : []
        }

    #Store latest fesible schedule
    lastFeasibleSchedule = schedule.copy()

    #Constraints to improve end-to-end reaction time by limiting the value found 
    limitEndtoEndConstraint = {}

    #Determine the hyperperiod of tasks
    hyperperiod = 1
    for t in system['TaskStore']:
        hyperperiod = math.lcm(hyperperiod, t['period'])
    print("System hyperperiod: " + str(hyperperiod))

    #The number of hyperperiod used for scheduler is to exceed the makespan
    factor = system['PluginParameters']['Makespan'] / hyperperiod
    factor = math.ceil(factor)
    hyperperiod = factor * hyperperiod 
    print("Problem scaled hyperperiod: " + str(hyperperiod))
    
    #very large number is the hyperperiod
    veryLargeNumber = hyperperiod


    #get a list of all task dependencies that does not include the environment
    taskDependenciesList = []
    for dep in system['DependencyStore']:
        dependencyName = dep['name']
        srcTask = dep['source']['task']
        destTask = dep['destination']['task']
        if (srcTask == '__system' or destTask == '__system'):
            continue
        taskDependencyPair = srcTask+"_"+destTask
        taskDependenciesList.append(taskDependencyPair)


    #variable to track number of iterations to find solution    
    timesRan = 0
    print("Initial Run ...")
    #go through each dependency and try to tighten the worst case end-to-end time
    for currentProcessingDependency in taskDependenciesList:

        #keep iterating ILP solver until no further optimisations can be found
        lookingForOptimalSolution = True
        #list of ILP constraint used to tighten the current dependency
        constraintReductionList = []
        while(lookingForOptimalSolution):
            print("Run ... "+currentProcessingDependency)
            timesRan = timesRan + 1

            #open to write new LP file
            if gurobi: 
                lp = GurobiLPWriter("system.lp", veryLargeNumber)
            else:
                lp = LPWriter("system.lp", veryLargeNumber)

            #objective to min End-To-End time
            lp.writeObjective("endToEndTime")



            #all task instances within the hyperperiod
            allTaskInstances = {}
            taskWCET = {}
            taskPeriod = {}

            #go over each task and create contraints for each task instance
            for t in system['TaskStore']:
                lp.writeComment("task properties")
                
                #get current task properties
                taskName = t['name']
                wcet = t['wcet']
                period = t['period']

                #store task properties in list
                taskWCET[taskName] = wcet
                taskPeriod[taskName] = period
                
                #for each instrance of the task within the hyperperiod
                instances = []
                i = 0
                for instanceStartTime in range(0, hyperperiod, period):
                    #task instance with integer identification
                    inst = taskName + "_" + str(i)
                    instances.append(inst)

                    #instance properties
                    instanceDeadline = instanceStartTime + period

                    #set up execution bounds constraint
                    lp.writeTaskInstanceExecutionBounds(str(taskName), inst, instanceStartTime, instanceDeadline, taskWCET[taskName], sameLETForAllInstances)

                    lp.intVaraibles.append("U"+inst + "_end_time")
                    lp.intVaraibles.append("U"+inst + "_start_time")
                    i = i + 1
                
                #maintain a list of instances assoicated to a task
                allTaskInstances[taskName] = instances
            
            #print("Task Instances: " + str(allTaskInstances))
            copyAllTaskInstances = allTaskInstances.copy()

            lp.writeComment("Make sure tasks do not overlap in execution")

            #Go over each task and make sure the task instances do not overlap in execution (single core)
            for t in system['TaskStore']:
                wcet = t['wcet']
                #get all instances of that task
                instances = copyAllTaskInstances.pop(t['name'])
                for inst in instances:
                    for key in copyAllTaskInstances.keys():
                        for other in copyAllTaskInstances[key]:
                            lp.writeTaskOverlapContraint(inst, other)
                            
                            
            lp.endToEndTimeSummation = ""
            lp.writeComment("Each destination task instance of an event chain can only be connected to one source")
            
            lp.endToEndConstraints = ""
            lp.endToEndTaskTable = {}

            #Iterate over each dependency
            for dep in system['DependencyStore']:

                #dependency parameters
                dependencyName = dep['name']
                srcTask = dep['source']['task']
                destTask = dep['destination']['task']

                #if the dependency is to the environment then ignore as there the environment can be sampled/emitted to anytime
                if (srcTask == '__system' or destTask == '__system'):
                    continue

                #get the instances of all source and destination tasks
                srcTaskInstances = allTaskInstances[srcTask]
                destTaskInstances = allTaskInstances[destTask]


                lp.writeComment(dependencyName)
                taskDependencyPair = srcTask+"_"+destTask

                lp.endToEndTaskTable[taskDependencyPair] = []

                #Create constraint that each event dependency task instance can only have 1 source task instance
                #Iterate over destination task instances
                
                lp.writeTaskDependencyContraint(srcTask, destTask, destTaskInstances, srcTaskInstances)

            lp.write(lp.endToEndConstraints)
            lp.writeObjectiveEquation()

            for key in limitEndtoEndConstraint:
                #The constraintReductionList contains dependency instance pairs of the currently processing dependency
                if gurobi:
                    if (key in constraintReductionList):
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]-1) + "\n")
                    else:
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]) + "\n")
                else:
                    if (key in constraintReductionList):
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]-1) + ";\n")
                    else:
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]) + ";\n")

            #lp.write(sumOfEndTimeString + " = "+ str(commutativeEndtime) +";\n")
            lp.writeBooleanConstraints()

            #ILP problem becomes very hard if large integer is used.
            #for i in intVaraibles:
            #    lp.write("int "+ i + ";\n")


            lp.close()

            if gurobi:
                results, lines = CallGurobi()
                #print(results)
            else:
                results, lines = CallLPSolve()
            print("Results:\n---")
            
            if len(results) == 0 :
                print("Problem not feasible.")
                lookingForOptimalSolution = False
                limitEndtoEndConstraint = {}
            else:
                print("Problem feasible.")
                print("Current best end-to-end total: "+ str(results["endToEndTime"]))
                limitEndtoEndConstraint, constraintReductionList = parseLPSolveResults(limitEndtoEndConstraint, currentProcessingDependency, lp, results)       
                #Export Schedule
                schedule = exportSchedule(system, schedule, lp, allTaskInstances, results)
                lastFeasibleSchedule = schedule.copy()
                print("---\n")
        #if all instances have the same offset there is no point to iterate for a solution as all solutions are the same        
            if (sameLETForAllInstances) :
                lookingForOptimalSolution = False
        if (sameLETForAllInstances) :
            break
    print("Ran "+str(timesRan) + " times")
    return lastFeasibleSchedule

def parseLPSolveResults(limitEndtoEndConstraint, currentProcessingDependency, lp, results):
    currentWorstChainTimes = {}

    #get current worst case end to end times for each task pair dependency
    for chain in lp.endToEndTaskTable.keys():
        constraints = lp.endToEndTaskTable[chain]
        for key in results.keys():
            if ("EtoE" in key):
                if key in constraints:
                    if ((chain in currentWorstChainTimes.keys()) == True):
                        if(currentWorstChainTimes[chain] <  float(results[key])):
                            currentWorstChainTimes[chain] = float(results[key])
                    else:
                        currentWorstChainTimes[chain] =  float(results[key])
                                

    constraintReductionList = []
    for chain in lp.endToEndTaskTable.keys():  
        constraints = lp.endToEndTaskTable[chain]
        for c in constraints:
            limitEndtoEndConstraint[c] = round(currentWorstChainTimes[chain])
            if (chain == currentProcessingDependency):
                constraintReductionList.append(c)
    return limitEndtoEndConstraint, constraintReductionList

def exportSchedule(system, schedule, lp, allTaskInstances, results):
    for t in system['TaskStore']:
        if (t['name']== "__system"):
            continue
        taskInstancesJson = {
                            "name" : t["name"],
                            "initialOffset" : 0,
                            }
        instances = allTaskInstances[t['name']]
        instancesLS = []
        i = 0 
        for inst in instances: 
            startTimeKey = lp.taskInstStartTime(inst)
            endTimeKey = lp.taskInstEndTime(inst)
            starttime = results[startTimeKey]
            endtime = results[endTimeKey]
            taskInstance = {
                            "instance" : i,
                            "periodStartTime" : round(float((i * int(t['period'])))),
                            "letStartTime" : round(float(starttime)),
                            "letEndTime" : round(float(endtime)),
                            "periodEndTime" : round(float((i+1) * int(t['period']))),
                            "executionTime": t['wcet'],
                            "executionIntervals": [ {
                                "startTime": round(float(starttime)),
                                "endTime": round(float(starttime)+ int(t['wcet']))
                            } ]
                        }
            i = i + 1
            instancesLS.append(taskInstance)
        taskInstancesJson["value"] = instancesLS 
        schedule["TaskInstancesStore"].append(taskInstancesJson)
    return schedule

def CallGurobi():
    results = {}
    with subprocess.Popen(["gurobi_cl",'ResultFile=gurobiresult.sol','system.lp'], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8") 
        if "Model is infeasible" in output:
            return {}, {}
        f = open("gurobiresult.sol", "r")
        data = f.read()
        lines = data.split("\n")

        for l in lines:
            if (len(l) == 0):
                continue
            fragment = re.split('\s+', l)
            results[fragment[0]] = fragment[1]
    return results,lines

def CallLPSolve():
    results = {}

    with subprocess.Popen(["lp_solve_5.5.2.11_exe_win64\lp_solve.exe",'system.lp','-ip'], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8") 
        #print(output)
        if "This problem is infeasible" in output:
            return {}, {}
        lines = output.split("\r\n")
        for l in lines:
            if (len(l) == 0):
                continue
            fragment = re.split('\s+', l)
            results[fragment[0]] = fragment[1]
    return results,lines




if __name__ == '__main__':
    print("Start LP Scheduler")
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", type=str, default="")
    parser.add_argument('-lpsolve', action='store_true')
    args = parser.parse_args()
    
    if args.lpsolve:
        gurobi = False
        print("Solver LPsolve")
    else:
        print("Solver Gruobi")

    if len(args.f) > 0:
        f = open(args.f)
        system = json.load(f)
        lpScheduler(system)
    else:
        hostName = "localhost"
        serverPort = 8181
        webServer = ThreadingHTTPServer((hostName, serverPort), server)
        print("Server started http://%s:%s" % (hostName, serverPort))

        try:
            webServer.serve_forever()
        except KeyboardInterrupt:
            pass
            
        webServer.server_close()
        print("Server stopped.")
    
