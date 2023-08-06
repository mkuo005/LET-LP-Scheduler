"""
This program converts a LetSyncrhonise system model into a set of linear programming 
constraints that can be solved to minimise the delays of task dependencies.
"""

# Import web server libraries
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socketserver 

# Import the required libraries
import sys
import traceback
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
    objectiveVariable = "sumDependencyDelays",
    individualLetInstanceParams = True  # Each instance of a LET task can have different parameters
)

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
            traceback.print_exc()
            self._set_error_headers("LetSynchronise system model could not be read")
            return
        
        try:
            system = json.loads(post_body.decode("utf-8"))
        except Exception:
            traceback.print_exc()
            self._set_error_headers("LetSynchronise system model could not be loaded")
            return
        
        try:
            schedule = lpScheduler(system)
            if schedule == None:
                raise Exception("LetSynchronise system is unschedulable!")
        except FileNotFoundError as error:
            traceback.print_exc()
            self._set_error_headers(error)
            return
        except Exception as error:
            traceback.print_exc()
            self._set_error_headers(f"LetSynchronise system model could not be scheduled: {error}")
            return
        
        self._set_headers()
        self.wfile.write(bytes(json.dumps(schedule), "utf-8"))

    def do_PUT(self):
        self.do_POST();


# FIXME: Refactor to generate LP information and then generate LP file in one go. 
# LP Scheduler
def lpScheduler(system):
    
    # Store last feasible task schedule
    lastFeasibleSchedule = None

    # Constraints to improve end-to-end reaction time by limiting the value found 
    delayVariableUpperBounds = {}

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
        taskDependencyPair = f"{dependency['source']['task']}_{dependency['destination']['task']}"
        if ("__system" in taskDependencyPair):
            continue
        taskDependenciesList.append(taskDependencyPair)


    # Track the number of iterations to find solution    
    timesRan = 0

    # FIXME: Why do we even need to iterate?
    # Iterate through each dependency and try to tighten the worst case end-to-end time
    for taskDependencyPair in taskDependenciesList:

        # Keep iterating LP solver until no further optimisations can be found
        lookingForOptimalSolution = True
        
        # List of LP constraint used to tighten the current dependency
        delayVariablesToTighten = []
        while lookingForOptimalSolution:
            print()
            print(f"Iteration {timesRan} ... {taskDependencyPair}")
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
                    # Task instance name includes an instance number
                    instanceName = f"{taskName}_{len(instances)}"
                    instances.append(instanceName)

                    # Compute task instance end time
                    instanceEndTime = instanceStartTime + taskPeriod
                    
                    # Encode the execution bounds of the task instance in LP constraints
                    lp.writeTaskInstanceExecutionBounds(taskName, instanceName, instanceStartTime, instanceEndTime, taskWcet, Config.individualLetInstanceParams)
                
                allTaskInstances[taskName] = instances
            
            lp.writeComment("Make sure task executions do not overlap")

            # Add pairwise task constraints to make sure task executions do not overlap (single core)
            allTaskInstancesCopy = allTaskInstances.copy()
            while bool(allTaskInstancesCopy):
                # Get all instances of that task
                taskName, instances = allTaskInstancesCopy.popitem()
                for instance in instances:
                    for key in allTaskInstancesCopy.keys():
                        for other in allTaskInstancesCopy[key]:
                            lp.writeTaskOverlapConstraint(instance, other)
            
            lp.writeComment("Each destination task instance of a dependency can only be connected to one source")

            # Constrain each event dependency task instance to only have one source task instance
            for dependency in system['DependencyStore']:

                # Dependency parameters
                name = dependency['name']
                srcTask = dependency['source']['task']
                destTask = dependency['destination']['task']

                # Dependencies to the environment are left unconstrained.
                if (srcTask == '__system' or destTask == '__system'):
                    continue

                # Get source and destination task instances
                srcTaskInstances = allTaskInstances[srcTask]
                destTaskInstances = allTaskInstances[destTask]

                lp.writeDependencySourceTaskSelectionConstraint(name, srcTask, srcTaskInstances, destTask, destTaskInstances)
            
            # FIXME: Refactor this into the for-loop above
            lp.writeComment("Dependency delays")
            lp.write(lp.dependencyDelayConstraints)
            
            lp.writeObjectiveEquation()

            # FIXME: Refactor into LP writers
            lp.writeComment("Tighten dependency delays")
            for delayVariable, delayValue in delayVariableUpperBounds.items():
                # Add constraints to tighten the current dependency pair to find better solutions.
                # delayVariablesToTighten contains names of the dependency pair instances that we want to reduce their delays.
                if (delayVariable in delayVariablesToTighten):
                    constraint = f"{delayVariable} <= {delayValue - 1}"
                else:
                    constraint = f"{delayVariable} <= {delayValue}"
                if Config.solver == Solver.GUROBI:
                    lp.write(f"{constraint}\n")
                elif Config.solver == Solver.LPSOLVE:
                    lp.write(f"{constraint};\n")

            # Create boolean variable constraint
            lp.writeBooleanConstraints()

            lp.close()

            # Call the LP solver
            if Config.solver == Solver.GUROBI:
                results, lines = CallGurobi()
            elif Config.solver == Solver.LPSOLVE:
                results, lines = CallLPSolve()
            
            print()
            print("Results:")
            print("--------")
            if len(results) == 0 :
                # If there are no results then the problem is infeasible
                print("LetSynchronise system is unschedulable!")
                
                # No need to try and tighten an infeasible problem
                lookingForOptimalSolution = False
                # FIXME: Why remove all upper bounds? Why not just the upper bounds of taskDependencyPair?
                delayVariableUpperBounds = {}
            else:
                # Problem is feasible
                print("LetSynchronise system is schedulable")
                print(f"Current summation of task dependency delays: {results['sumDependencyDelays']} ns")
                
                # Create the task schedule that is encoded in the LP solution
                lastFeasibleSchedule = exportSchedule(system, lp, allTaskInstances, results)

                # Determine new constraints needed to tighten the dependency delays in the next iteration 
                delayVariablesToTighten = lp.dependencyTaskTable[taskDependencyPair]
                delayVariableUpperBounds = parseLpResults(lp, results)       
            print("--------")
                
            # If all instances of a LET task share the same parameters, then no more improvements are possible.
            if not Config.individualLetInstanceParams:
                lookingForOptimalSolution = False

        if not Config.individualLetInstanceParams:
            break
            
    print(f"Iterated a total of {timesRan} times")
    return lastFeasibleSchedule

def parseLpResults(lp, results):
    delayResults = {solutionVariable: solutionValue for solutionVariable, solutionValue in results.items() if "EtoE_" in solutionVariable}
    
    # Get the max delay of each task dependency instance
    maxDependencyDelays = {}
    for dependency, delayVariables in lp.dependencyTaskTable.items():
        maxDependencyDelays[dependency] = -1
        for solutionVariable, solutionValue in delayResults.items():
            if solutionVariable in delayVariables:
                maxDependencyDelays[dependency] = max(maxDependencyDelays[dependency], float(solutionValue))
    
    # Get new upper bounds for each task dependency instance
    delayVariableUpperBounds = {}
    for dependency, delayVariables in lp.dependencyTaskTable.items():        
        for delayVariable in delayVariables:
            delayVariableUpperBounds[delayVariable] = round(maxDependencyDelays[dependency])
    
    return delayVariableUpperBounds

def exportSchedule(system, lp, allTaskInstances, results):
    schedule = {
        "TaskInstancesStore" : []
    }
    
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
        if not "Model is infeasible" in output:
            data = open("gurobiresult.sol", "r").read()
            lines = filter(lambda line: len(line) != 0, data.splitlines())
            for line in lines:
                fragment = re.split('\s+', line)
                results[fragment[0]] = fragment[1] # Create dictionary of variables and their solutions
    return results, lines

# Call LpSolve and parse the result
def CallLPSolve():
    results = {}
    lines = []
    with subprocess.Popen([Config.solverProg, Config.lpFile, '-ip'], stdout=subprocess.PIPE) as proc:
        output = proc.stdout.read().decode("utf-8")
        if not "This problem is infeasible" in output:
            lines = filter(lambda line: len(line) != 0, output.splitlines())
            for line in lines:
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
    
