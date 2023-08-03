"""
This projects converts LetSyncrhonise tasks into linear programming constraints to find an optiminal schedule
"""


# Import web server libraries
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socketserver 

# Import the required libraries
import time
import argparse
import json
import math
import subprocess
import re

# Import LPSolve constraint generator
from LPWriter import LPWriter

# Import Gurobi constraint generator
from GurobiLPWriter import GurobiLPWriter

# Tool configurations

# Use Gurobi styled LP constraints
gurobi = True

# Restrict that all instances of a task have the same LET parameters
sameLETForAllInstances = True

# Webserver to handle requests from LetSyncrhonise LP plugin
class server(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        #Allow cross origin headers
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS, POST')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
    def end_headers (self):
        #Allow cross origin headers
        self.send_header('Access-Control-Allow-Origin', '*')
        BaseHTTPRequestHandler.end_headers(self)
        
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
    def _set_error_headers(self):
        self.send_response(501, "Scheduler does not support posted LET system")
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
    def do_GET(self):
        self._set_headers()
        self.wfile.write("received get request")
        
    def do_POST(self):
        '''Reads post request body'''
        content_len = int(self.headers.get('content-length'))
        post_body = self.rfile.read(content_len)
        system = json.loads(post_body.decode("utf-8"))
        schedule = lpScheduler(system)
        if (schedule == None):
            self._set_error_headers()
        else:
            self._set_headers()
            self.wfile.write(bytes(json.dumps(schedule),"utf-8"))

    def do_PUT(self):
        self.do_POST();



# LP Scheduler
def lpScheduler(system):
    
    # Initial empty schedule
    schedule = {
        "DependencyInstancesStore" : [], 
        "EventChainInstanceStore" : [],
        "TaskInstancesStore" : []
        }

    # Store latest fesible schedule
    lastFeasibleSchedule = schedule.copy()

    # Constraints to improve end-to-end reaction time by limiting the value found 
    limitEndtoEndConstraint = {}

    # Determine the hyperperiod of tasks
    hyperperiod = 1
    for t in system['TaskStore']:
        hyperperiod = math.lcm(hyperperiod, t['period'])
    print("System hyperperiod: " + str(hyperperiod))

    # The number of hyperperiod used for scheduler is to exceed the makespan as event chains can span across mutiple hyperperiods
    factor = system['PluginParameters']['Makespan'] / hyperperiod
    factor = math.ceil(factor)
    hyperperiod = factor * hyperperiod 
    print("Hyperperiod scaled by makespan: " + str(hyperperiod))
    
    # Very large number is the scaled hyperperiod as task parameters cannot exceed the scaled hyperperiod
    veryLargeNumber = hyperperiod


    # Get a list of all task dependencies that does not include the environment '__system'
    taskDependenciesList = []
    for dependency in system['DependencyStore']:
        name = dependency['name']
        srcTask = dependency['source']['task']
        destTask = dependency['destination']['task']
        if (srcTask == '__system' or destTask == '__system'):
            continue
        taskDependencyPair = srcTask+"_"+destTask
        taskDependenciesList.append(taskDependencyPair)


    # Variable to track number of iterations to find solution    
    timesRan = 0
    print("Initial Run ...")

    # Illiterate through each dependency and try to tighten the worst case end-to-end time
    for currentProcessingDependency in taskDependenciesList:

        # Keep iterating ILP solver until no further optimisations can be found
        lookingForOptimalSolution = True
        # List of ILP constraint used to tighten the current dependency
        constraintReductionList = []
        while(lookingForOptimalSolution):
            print("Run ... "+currentProcessingDependency)
            timesRan = timesRan + 1

            # Create LP writer for the selected solver
            if gurobi: 
                lp = GurobiLPWriter("system.lp", veryLargeNumber)
            else:
                lp = LPWriter("system.lp", veryLargeNumber)

            # Create the objective to minimize End-To-End time
            lp.writeObjective("endToEndTime")

            # All task instances within the hyperperiod
            allTaskInstances = {}
            taskWCET = {}
            taskPeriod = {}

            # Encode the task parameters in to LP contraints
            # Go over each task and create contraints for each task instance
            for t in system['TaskStore']:
                lp.writeComment("task properties")
                
                # Get current task properties
                taskName = t['name']
                wcet = t['wcet']
                period = t['period']

                # Store task properties in list
                taskWCET[taskName] = wcet
                taskPeriod[taskName] = period
                
                # For each instrance of the task within the hyperperiod
                instances = []
                i = 0
                for instanceStartTime in range(0, hyperperiod, period):
                    # Task instances will be named by incrementing an integer index
                    inst = taskName + "_" + str(i)
                    instances.append(inst)

                    # Computer task instance properties
                    # Computer the task instance deadline
                    instanceDeadline = instanceStartTime + period
                    # Encode the execution bounds of the task instance in LP constraints
                    lp.writeTaskInstanceExecutionBounds(str(taskName), inst, instanceStartTime, instanceDeadline, taskWCET[taskName], sameLETForAllInstances)

                    # The append list of unknown integer variables with the instance start and end times
                    lp.intVaraibles.append("U"+inst + "_end_time")
                    lp.intVaraibles.append("U"+inst + "_start_time")
                    i = i + 1
                
                # Maintain a list of instances assoicated to a task
                allTaskInstances[taskName] = instances
            
            # create a copy of all task instances for manipulation
            copyAllTaskInstances = allTaskInstances.copy()

            lp.writeComment("Make sure tasks do not overlap in execution")

            # Go over each task and make sure the task instances do not overlap in execution (single core)
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

            # Iterate over each dependency
            for dependency in system['DependencyStore']:

                # Dependency parameters
                name = dependency['name']
                srcTask = dependency['source']['task']
                destTask = dependency['destination']['task']

                # If the dependency is to the environment then ignore as there the environment can be sampled/emitted to anytime
                if (srcTask == '__system' or destTask == '__system'):
                    continue

                # Get the instances of all source and destination tasks
                srcTaskInstances = allTaskInstances[srcTask]
                destTaskInstances = allTaskInstances[destTask]


                lp.writeComment(name)
                taskDependencyPair = srcTask+"_"+destTask

                lp.endToEndTaskTable[taskDependencyPair] = []

                # Create constraint that each event dependency task instance can only have 1 source task instance
                # Iterate over destination task instances
                lp.writeTaskDependencyContraint(srcTask, destTask, destTaskInstances, srcTaskInstances)

            lp.write(lp.endToEndConstraints)
            lp.writeObjectiveEquation()

            for key in limitEndtoEndConstraint:
                # The constraintReductionList contains dependency instances pairs of the currently processing dependency to improve the end-to-end time
                # Tighten the constraint for this dependency to see if there are tighter better solutions
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

            # Create boolean variable constraint
            lp.writeBooleanConstraints()

            # Commented out so that unknown variables are left as real numbers rather then integers.
            # No need to restrict problem to ILP state space as it will cause unesscessary complexity
            #for i in intVaraibles:
            #    lp.write("int "+ i + ";\n")

            lp.close()

            # call solvers
            if gurobi:
                results, lines = CallGurobi()
            else:
                results, lines = CallLPSolve()
            print("Results:\n---")
            
            if len(results) == 0 :
                # If there are no results then the problem must be infeasible
                print("Problem not feasible.")
                
                # No need to try and tighten an infesaible problem
                lookingForOptimalSolution = False
                limitEndtoEndConstraint = {}
            else:
                # Problem is feasible
                print("Problem feasible.")
                print("Current best end-to-end total: "+ str(results["endToEndTime"]))
                
                # Parse result schedule from LP solution
                limitEndtoEndConstraint, constraintReductionList = parseLPSolveResults(limitEndtoEndConstraint, currentProcessingDependency, lp, results)       
                
                # Store the currently best schedule
                schedule = exportSchedule(system, schedule, lp, allTaskInstances, results)
                lastFeasibleSchedule = schedule.copy()
                print("---\n")
                
            #if all instances have the same offset there is no point to iterate for a solution as all solutions are the same as any solution is as good as another
            if (sameLETForAllInstances) :
                lookingForOptimalSolution = False
        if (sameLETForAllInstances) :
            break
            
    print("Ran "+str(timesRan) + " times")
    return lastFeasibleSchedule

def parseLPSolveResults(limitEndtoEndConstraint, currentProcessingDependency, lp, results):
    currentWorstChainTimes = {}

    # Get current worst case end-to-end times for each task pair dependency
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



# Call Gurobi solver and parse result
def CallGurobi():
    results = {}
    with subprocess.Popen(["gurobi_cl",'ResultFile=gurobiresult.sol','system.lp'], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8") 
        if "Model is infeasible" in output:
            return {}, {}
        else:
            f = open("gurobiresult.sol", "r")
            data = f.read()
            lines = data.split("\n")

            for l in lines:
                if (len(l) == 0):
                    continue
                fragment = re.split('\s+', l)
                results[fragment[0]] = fragment[1] # Create dictionary of variable and its solutions
    return results,lines

# Call LPSolve solver and parse result
def CallLPSolve():
    results = {}
    with subprocess.Popen(["lp_solve_5.5.2.11_exe_win64\lp_solve.exe",'system.lp','-ip'], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8") 
        #print(output)
        if "This problem is infeasible" in output:
            return {}, {}
        else:
            lines = output.split("\r\n")
            for l in lines:
                if (len(l) == 0):
                    continue
                fragment = re.split('\s+', l)
                results[fragment[0]] = fragment[1]  # Create dictionary of variable and its solutions
    return results,lines



if __name__ == '__main__':
    print("Start LP Scheduler")
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", type=str, default="")
    parser.add_argument('-lpsolve', action='store_true')
    args = parser.parse_args()
    
    # select contraint type
    if args.lpsolve:
        gurobi = False
        print("Solver LPsolve")
    else:
        gurobi = True
        print("Solver Gruobi")

    # Specify the LET system file to create schedule for, or run in webserver mode for the plugin.
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
    
