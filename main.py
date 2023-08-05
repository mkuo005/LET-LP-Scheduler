"""
This program converts a LetSyncrhonise system model into a set of linear programming 
constraints that can be solved to minimise the delays of task dependencies.
"""

# Import web server libraries
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socketserver 

# Import the required libraries
import sys
import subprocess
import argparse
import re
import json
import math
from enum import Enum
from types import SimpleNamespace

# Import LpSolve constraint generator
from LpSolveLPWriter import LpSolveLPWriter

# Import Gurobi constraint generator
from GurobiLPWriter import GurobiLPWriter

# Tool configuration
class Solver(Enum):
    NONE = 0
    GUROBI = 1
    LPSOLVE = 2

SolverProg = [
    "none",
    "gurobi_cl",
    "lp_solve"
]

Config = SimpleNamespace(
    hostName = "localhost",
    serverPort = 8181,
    solver = Solver.NONE,
    solveProg = "",
    os = "",
    exeSuffix = "",
    lpFile = "system.lp",
    objectiveVariable = "sumDependencyDelays"
)

# Restrict that all instances of a task have the same LET parameters
sameLETForAllInstances = True

# Web server to handle requests from the LetSyncrhonise LP plugin, 
# ls.plugin.goal.ilp.js
# https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.ilp.js
class Server(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Allow cross origin headers
        self.send_response(200, "ok")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS, POST")
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        
    def end_headers(self):
        # Allow cross origin headers
        self.send_header("Access-Control-Allow-Origin", "*")
        BaseHTTPRequestHandler.end_headers(self)
        
    def _set_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
    def _set_error_headers(self, message):
        self.send_response(501, message)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
    def do_GET(self):
        self._set_headers()
        self.wfile.write(bytes("LET-LP-Scheduler", "utf-8"))
        
    # FIXME: Add descriptive errors!!!
    def do_POST(self):
        '''Reads POST request body'''
        try:
            content_len = int(self.headers.get("content-length"))
            post_body = self.rfile.read(content_len)
        except Exception:
            self._set_error_headers("LetSynchronise system model could not be read")
            return
        
        try:
            system = json.loads(post_body.decode("utf-8"))
        except Exception:
            self._set_error_headers("LetSynchronise system model could not be loaded")
            return
        
        try:
            schedule = lpScheduler(system)
        except FileNotFoundError as error:
            self._set_error_headers(error)
            return
        except Exception as error:
            self._set_error_headers(f"LetSynchronise system model could not be scheduled: {error}")
            return
        
        self._set_headers()
        self.wfile.write(bytes(json.dumps(schedule), "utf-8"))

    def do_PUT(self):
        self.do_POST();


# LP Scheduler
def lpScheduler(system):
    
    # Initial empty schedule
    schedule = {
        "TaskInstancesStore" : []
    }

    # Store last feasible task schedule
    lastFeasibleSchedule = schedule.copy()

    # Constraints to improve end-to-end reaction time by limiting the value found 
    limitEndtoEndConstraint = {}

    # Determine the hyper-period of the tasks
    taskPeriods = [task['period'] for task in system['TaskStore']]
    hyperPeriod = math.lcm(*taskPeriods)
    print(f"System hyper-period: {hyperPeriod} ns")

    # The task schedule is analysed over a scheduling window, starting at 0 ns and 
    # ending at the makespan, rounded up to the next hyper-period.
    # Limitation: End-to-end constraints where none of their instances appears within 
    # the scheduling window will not be optimised.
    makespan = system['PluginParameters']['Makespan']
    schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod
    print(f"Scheduling window: {schedulingWindow} ns")
    
    # A large constant, equal to the scheduling window, is needed when normalising logical disjunctions in LP constraints.
    lpLargeConstant = schedulingWindow

    # Get all task dependencies that do not involve system inputs or outputs ("__system") 
    taskDependenciesList = []
    for dependency in system['DependencyStore']:
        taskDependencyPair = f"{dependency['source']['task']} --> {dependency['destination']['task']}"
        if ("__system" in taskDependencyPair):
            continue
        taskDependenciesList.append(taskDependencyPair)


    # Track the number of iterations to find solution    
    timesRan = 0
    print()

    # Iterate through each dependency and try to tighten the worst case end-to-end time
    for currentProcessingDependency in taskDependenciesList:

        # Keep iterating ILP solver until no further optimisations can be found
        lookingForOptimalSolution = True
        
        # List of ILP constraint used to tighten the current dependency
        constraintReductionList = []
        while lookingForOptimalSolution:
            print(f"Iteration {timesRan} ... {currentProcessingDependency}")
            timesRan += 1

            # Create LP writer for the selected solver
            if Config.solver == Solver.GUROBI: 
                lp = GurobiLPWriter(Config.lpFile, Config.objectiveVariable, lpLargeConstant)
            elif Config.solver == Solver.LPSOLVE:
                lp = LpSolveLPWriter(Config.lpFile, Config.objectiveVariable, lpLargeConstant)

            # Create the objective to minimize task dependency delay
            lp.writeObjective()

            # All task instances within the scheduling window
            allTaskInstances = {}

            # Encode the task instances over the scheduling window as LP constraints
            for task in system['TaskStore']:
                # Get task parameters
                taskName = task['name']
                taskWcet = task['wcet']
                taskPeriod = task['period']
                
                lp.writeComment(f"Task instance properties of {taskName}")
                
                # Create the task instances that appear inside the scheduling window
                instances = []
                for instanceStartTime in range(0, schedulingWindow, taskPeriod):
                    # Task instances will be named by incrementing an integer index
                    instanceName = f"{taskName}_{len(instances)}"
                    instances.append(instanceName)

                    # Compute task instance end time
                    instanceEndTime = instanceStartTime + taskPeriod
                    
                    # Encode the execution bounds of the task instance in LP constraints
                    lp.writeTaskInstanceExecutionBounds(taskName, instanceName, instanceStartTime, instanceEndTime, taskWcet, sameLETForAllInstances)
                
                # Maintain a list of instances for each task
                allTaskInstances[taskName] = instances
            
            # create a copy of all task instances for manipulation
            copyAllTaskInstances = allTaskInstances.copy()

            lp.writeComment("Make sure task executions do not overlap")

            # Go over each task and make sure the task instances do not overlap in execution (single core)
            for task in system['TaskStore']:
                # Get all instances of that task
                instances = copyAllTaskInstances.pop(task['name'])
                for instance in instances:
                    for key in copyAllTaskInstances.keys():
                        for other in copyAllTaskInstances[key]:
                            lp.writeTaskOverlapConstraint(instance, other)
                            
                            
            lp.dependencyDelaysSum = ""
            lp.writeComment("Each destination task instance of a dependency can only be connected to one source")
            
            lp.dependencyConstraints = ""
            lp.dependencyTaskTable = {}

            # Iterate over each dependency
            for dependency in system['DependencyStore']:

                # Dependency parameters
                name = dependency['name']
                srcTask = dependency['source']['task']
                destTask = dependency['destination']['task']

                # Dependencies to the environment are left unconstrained.
                if (srcTask == '__system' or destTask == '__system'):
                    continue

                # Get the instances of all source and destination tasks
                srcTaskInstances = allTaskInstances[srcTask]
                destTaskInstances = allTaskInstances[destTask]


                lp.writeComment(name)
                taskDependencyPair = srcTask+"_"+destTask

                lp.dependencyTaskTable[taskDependencyPair] = []

                # Create constraint that each event dependency task instance can only have 1 source task instance
                # Iterate over destination task instances
                lp.writeTaskDependencyConstraint(srcTask, destTask, destTaskInstances, srcTaskInstances)

            lp.write(lp.dependencyConstraints)
            lp.writeObjectiveEquation()

            for key in limitEndtoEndConstraint:
                # The constraintReductionList contains dependency instances pairs of the currently processing dependency to improve the end-to-end time
                # Tighten the constraint for this dependency to see if there are tighter better solutions
                if Config.solver == Solver.GUROBI:
                    if (key in constraintReductionList):
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]-1) + "\n")
                    else:
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]) + "\n")
                elif Config.solver == Solver.LPSOLVE:
                    if (key in constraintReductionList):
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]-1) + ";\n")
                    else:
                        lp.write(key + " <= " + str(limitEndtoEndConstraint[key]) + ";\n")

            # Create boolean variable constraint
            lp.writeBooleanConstraints()

            # Commented out so that unknown variables are left as real numbers rather then integers.
            # No need to restrict problem to ILP state space as it will cause unnesscessary complexity
            #for i in intVariables:
            #    lp.write("int "+ i + ";\n")

            lp.close()

            # call solvers
            if Config.solver == Solver.GUROBI:
                results, lines = CallGurobi()
            elif Config.solver == Solver.LPSOLVE:
                results, lines = CallLPSolve()
            print()
            print("Results:")
            print("--------")
            
            if len(results) == 0 :
                # If there are no results then the problem must be infeasible
                print("Problem is infeasible")
                
                # No need to try and tighten an infeasible problem
                lookingForOptimalSolution = False
                limitEndtoEndConstraint = {}
            else:
                # Problem is feasible
                print("Problem is feasible")
                print(f"Current summation of task dependency delays: {results['sumDependencyDelays']} ns")
                
                # Create the task schedule from the LP solution
                limitEndtoEndConstraint, constraintReductionList = parseLPSolveResults(limitEndtoEndConstraint, currentProcessingDependency, lp, results)       
                
                # Export the best task schedule
                schedule = exportSchedule(system, schedule, lp, allTaskInstances, results)
                lastFeasibleSchedule = schedule.copy()
                print("--------")
                
            # If all instances have the same offset there is no point to iterate for a solution as all solutions are the same as any solution is as good as another
            if sameLETForAllInstances:
                lookingForOptimalSolution = False

        if sameLETForAllInstances:
            break
            
    print(f"Iterated a total of {timesRan} times")
    return lastFeasibleSchedule

def parseLPSolveResults(limitEndtoEndConstraint, currentProcessingDependency, lp, results):
    currentWorstChainTimes = {}

    # Get current worst case end-to-end times for each task pair dependency
    for dependency in lp.dependencyTaskTable.keys():
        constraints = lp.dependencyTaskTable[dependency]
        for key in results.keys():
            if ("EtoE" in key):
                if key in constraints:
                    if ((dependency in currentWorstChainTimes.keys()) == True):
                        if(currentWorstChainTimes[dependency] <  float(results[key])):
                            currentWorstChainTimes[dependency] = float(results[key])
                    else:
                        currentWorstChainTimes[dependency] =  float(results[key])

    constraintReductionList = []
    for dependency in lp.dependencyTaskTable.keys():  
        constraints = lp.dependencyTaskTable[dependency]
        for c in constraints:
            limitEndtoEndConstraint[c] = round(currentWorstChainTimes[dependency])
            if (dependency == currentProcessingDependency):
                constraintReductionList.append(c)
    return limitEndtoEndConstraint, constraintReductionList

def exportSchedule(system, schedule, lp, allTaskInstances, results):
    for task in system['TaskStore']:
        if (task['name'] == "__system"):
            continue
        
        taskInstancesJson = {
            "name": task['name'],
            "value": []
        }
        
        for instance in allTaskInstances[task['name']]: 
            index = len(taskInstancesJson['value'])
            startTimeKey = lp.taskInstStartTime(instance)
            endTimeKey = lp.taskInstEndTime(instance)

            # FIXME: Unsafe rounding! End times could exceed original task period
            startTime = round(float(results[startTimeKey]))
            endTime = round(float(results[endTimeKey]))
            period = int(task['period'])
            wcet = int(task['wcet'])
            
            taskInstance = {
                "instance" : index,
                "periodStartTime" : index * period,
                "letStartTime" : startTime,
                "letEndTime" : endTime,
                "periodEndTime" : (index + 1) * period,
                "executionTime": task['wcet'],
                "executionIntervals": [ {
                    "startTime": startTime,
                    "endTime": startTime + wcet
                } ]
            }
            taskInstancesJson['value'].append(taskInstance)
        schedule['TaskInstancesStore'].append(taskInstancesJson)
    return schedule

# Call Gurobi and parse the result
def CallGurobi():
    results = {}
    lines = []
    with subprocess.Popen([Config.solverProg, "ResultFile=gurobiresult.sol", Config.lpFile], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8")
        if "Model is infeasible" in output:
            print("LetSynchronise system is unschedulable!")
            raise Exception("LetSynchronise system is unschedulable!")
        
        data = open("gurobiresult.sol", "r").read()
        lines = data.splitlines()
        for line in lines:
            if (len(line) == 0):
                continue
            fragment = re.split('\s+', line)
            results[fragment[0]] = fragment[1] # Create dictionary of variables and their solutions
    return results, lines

# Call LpSolve and parse the result
def CallLPSolve():
    results = {}
    lines = []
    with subprocess.Popen([Config.solverProg, Config.lpFile, '-ip'], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8")
        if "This problem is infeasible" in output:
            print("LetSynchronise system is unschedulable!")
            raise Exception("LetSynchronise system is unschedulable!")
        
        lines = output.splitlines()
        for line in lines:
            if (len(line) == 0):
                continue
            fragment = re.split('\s+', line)
            results[fragment[0]] = fragment[1]  # Create dictionary of variables and their solutions
    return results, lines


if __name__ == '__main__':
    print("LET-LP-Scheduler")
    print("----------------")
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default="")
    parser.add_argument("--solver", choices=["gurobi", "lpsolve"], type=str, required=True)
    args = parser.parse_args()
    
   # Set the OS and executable file suffix
    Config.os = sys.platform
    if Config.os == "win32":
        Config.exeSuffix = ".exe"
    
    # Set the LP solver
    if args.solver == "lpsolve":
        Config.solver = Solver.LPSOLVE
        Config.solverProg = SolverProg[Solver.LPSOLVE.value] + Config.exeSuffix
    elif args.solver == "gurobi":
        Config.solver = Solver.GUROBI
        Config.solverProg = SolverProg[Solver.GUROBI.value]
    print(f"Solver: {Config.solverProg}")

    # Specify a LET system model file and create a schedule, or run in webserver mode for the LetSynchronise plugin.
    if len(args.file) > 0:
        try:
            file = open(args.file)
            system = json.load(file)
            lpScheduler(system)
        except FileNotFoundError:
            print(f"Unable to open \"{args.file}\"!")
    else:
        webServer = ThreadingHTTPServer((Config.hostName, Config.serverPort), Server)
        print(f"Server started at http://{Config.hostName}:{Config.serverPort}")
        print()

        try:
            webServer.serve_forever()
        except KeyboardInterrupt:
            pass
            
        webServer.server_close()
        print("Server stopped")
    
