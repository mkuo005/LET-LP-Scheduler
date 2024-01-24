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
import pulp as pl
from enum import Enum
from types import SimpleNamespace


# Import PuLP constraint generator
from PuLPWriter import PuLPWriter

# Tool configuration
class Solver(Enum):
    NONE = 0
    GUROBI = 1
    PULP = 2


Config = SimpleNamespace(
    hostName = "localhost",
    serverPort = 8181,
    solver = Solver.NONE,
    solveProg = "",
    os = "",
    exeSuffix = "",
    lpFile = "system.lp",
    objectiveVariable = "sumDependencyDelays",
    individualLetInstanceParams = False,  # Each instance of a LET task can have different parameters
    useOffSet = False # Enable task offset
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


# LP Scheduler
def lpScheduler(system):
    # Determine the hyper-period of the tasks
    taskPeriods = [task['period'] for task in system['TaskStore']]
    hyperPeriod = math.lcm(*taskPeriods)
    print(f"System hyper-period: {hyperPeriod} ns")

    # The task schedule is analysed over a scheduling window, starting at 0 ns and 
    # ending at the makespan, rounded up to the next hyper-period.
    makespan = system['PluginParameters']['Makespan']
    schedulingWindow = math.ceil(makespan / hyperPeriod) * hyperPeriod
    print(f"Scheduling window: {schedulingWindow} ns")
    
    # A large constant, equal to the scheduling window, is needed when normalising logical disjunctions in LP constraints.
    lpLargeConstant = schedulingWindow

    # Get all task dependencies that do not involve system inputs or outputs ("__system") 
    taskDependenciesList = set()
    for dependency in system['DependencyStore']:
        taskDependencyPair = f"{dependency['source']['task']}_{dependency['destination']['task']}"
        if ("__system" in taskDependencyPair):
            continue
        taskDependenciesList.add(taskDependencyPair)

    # Store last feasible task schedule
    lastFeasibleSchedule = None

    # Store the names of the dependency pair instances that we want to reduce their delays.
    delayVariableUpperBounds = {}

    # Track the number of iterations to find solution    
    timesRan = 0

    # FIXME: Why do we even need to iterate?
    # Iterate through each dependency and try to tighten the task dependency delays
    for taskDependencyPair in taskDependenciesList:
        # Keep iterating LP solver until no further optimisations can be found
        lookingForBetterSolution = True
        
        # List of LP constraint used to tighten the current dependency
        delayVariablesToTighten = []

        # Last summation of task dependency delays
        lastDelays = -1
        
        while lookingForBetterSolution:
            print()
            print(f"Iteration {timesRan} ... {taskDependencyPair}")
            timesRan += 1

            # Create LP writer for the selected solver
            lp = PuLPWriter(Config.lpFile, Config.objectiveVariable, lpLargeConstant)

            # Create the objective to minimize task dependency delay
            lp.writeObjective()

            # Equestion 2
            # Encode the task instances over the scheduling window as LP constraints
            # Return all task instances within the scheduling window
            allTaskInstances = lp.createTaskInstancesAsConstraints(system, schedulingWindow, Config)
            
            # Equestion 3
            # Create constraints that ensures no two tasks overlap (Single Core)
            if (system.get("CoreStore") is not None):
                lp.createTaskExecutionConstraints(allTaskInstances.copy(), system.get("CoreStore"))
            else:
                lp.createTaskExecutionConstraints(allTaskInstances.copy(), [{'name': 'c1', 'speedup': 1}]) #needed for old version of the exported file before multicore support

            # Equestion 4
            # A dependency instance is simply a pair of source and destination task instances
            # Each dependency instance can only have 1 source task but can have mutiple destinations
            # The selected source tasks must complete its execution before the destination task
            lp.createTaskDependencyConstraints(system, allTaskInstances)

            # Tightening delays is only required if tasks are scheduled independently of other instances within the period
            if Config.individualLetInstanceParams:
                lp.writeComment("Tighten dependency delays")
                for delayVariable, delayValue in delayVariableUpperBounds.items():
                    # Add constraints to tighten the current dependency pair to find better solutions.
                    lp.writeDelayConstraints(delayVariable, delayValue, delayVariable in delayVariablesToTighten)
            
            # Create objective equation has to be called after createTaskDependencyConstraints as the depenedency selection varaibles are needed to compute the summed end-to-end time
            lp.writeObjectiveEquation()
            
            # Call the LP solver
            results = {}
            if Config.solver == Solver.GUROBI:
                lp.solve(pl.GUROBI())
            elif Config.solver == Solver.PULP:
                lp.solve(None) # uses the default PuLP solver
            if (lp.prob.status == 1): 
                for v in lp.prob.variables():
                    results[str(v.name)] = v.varValue

            print("Results:")
            if len(results) == 0 :
                # If there are no results, then the problem is infeasible
                print("LetSynchronise system is unschedulable!")
                
                # No need to try and tighten an infeasible problem
                lookingForBetterSolution = False
                # FIXME: Why remove all upper bounds? Why not just the upper bounds of taskDependencyPair?
                delayVariableUpperBounds = {}
            else:
                # Problem is feasible
                print("LetSynchronise system is schedulable")
                print(f"Current summation of task dependency delays: {results[Config.objectiveVariable]} ns")
                lastDelays = results[Config.objectiveVariable]
                # Create the task schedule that is encoded in the LP solution
                lastFeasibleSchedule = exportSchedule(system, lp, allTaskInstances, results)

                # Determine upper bounds needed to tighten the dependency delays in the next iteration 
                delayVariablesToTighten = lp.dependencyInstanceDelayVariables[taskDependencyPair]
                delayVariableUpperBounds = tightenProblemSpace(lp, results)       
            print("--------")
                
            # If all instances of a LET task share the same parameters, then no more improvements are possible.
            if not Config.individualLetInstanceParams:
                lookingForBetterSolution = False

        if not Config.individualLetInstanceParams:
            break
            
    print(f"Iterated a total of {timesRan} times")
    print(f"Final summation of task dependency delays: {lastDelays} ns")
    return lastFeasibleSchedule

def tightenProblemSpace(lp, results):
    delayResults = {solutionVariable: solutionValue for solutionVariable, solutionValue in results.items() if "delay_" in solutionVariable}
    
    # Get the max delay of each task dependency instance
    maxDependencyDelays = {}
    for dependency, delayVariables in lp.dependencyInstanceDelayVariables.items():
        maxDependencyDelays[dependency] = -1
        for solutionVariable, solutionValue in delayResults.items():
            if solutionVariable in delayVariables:
                maxDependencyDelays[dependency] = max(maxDependencyDelays[dependency], float(solutionValue))
    
    # Get new upper bounds for each task dependency instance
    delayVariableUpperBounds = {}
    for dependency, delayVariables in lp.dependencyInstanceDelayVariables.items():        
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




if __name__ == '__main__':
    print("LET-LP-Scheduler")
    print("----------------")
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default="")
    parser.add_argument("--solver", choices=["gurobi", "pulp"], type=str, required=True)
    args = parser.parse_args()
    
   # Set the OS and executable file suffix
    Config.os = sys.platform
    if Config.os == "win32":
        Config.exeSuffix = ".exe"
    
    # Set the LP solver
    if args.solver == "gurobi":
        Config.solver = Solver.GUROBI
    elif args.solver == "pulp":
        Config.solver = Solver.PULP
    print(f"Solver: {Config.solver}")

    # Specify a LET system model file and create a schedule, or run in webserver mode for the LetSynchronise plugin.
    if len(args.file) > 0:
        try:
            file = open(args.file)
            system = json.load(file)
            system['PluginParameters'] = {'Makespan': 1} #make makespan equal to hyperperiod
            schedule = lpScheduler(system)
            scheduleFile = open("schedule.json", "w+")
            scheduleFile.write(json.dumps(schedule, indent=2))
            scheduleFile.close()
            
        except FileNotFoundError as e:
            print(f"Unable to open \"{args.file}\"!")
            print(e)
            traceback.print_exc()
            
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
    
