"""
This program converts a LetSyncrhonise system model into a set of linear programming 
constraints that can be solved to minimise the delays of task dependencies.

See the following paper for the original ILP formulation:
E. Yip and M. M. Y. Kuo. LetSynchronise: An Open-Source Framework for Analysing and 
Optimising Logical Execution Time Systems. CPS-IoT Week, 2023. Available online at
https://dl.acm.org/doi/10.1145/3576914.3587500

The formulation in this implementation supports multicores as well.
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

from multicore import MultiCoreScheduler


Config = SimpleNamespace(
    hostName = "localhost",
    serverPort = 8181,
    solveProg = "",
    os = "",
    exeSuffix = "",
    lpFile = "system.lp",
    objectiveVariable = "sumDependencyDelays",
    individualLetInstanceParams = False,  # Each instance of a LET task can have different parameters
    useOffSet = True, # Enable task offset
    useHeterogeneousCores = True,
    restrictTaskInstancesToSameCore = True,
    objectiveType = PuLPWriter.OVERALL_END_TO_END,
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
            inputFile = open("input_system.json", "w+")
            inputFile.write(json.dumps(system, indent=2))
            inputFile.close()
            schedule = None
            status = None
            if self.path and self.path == '/ilp':
                status, schedule = lpScheduler(system)
            if self.path and self.path == '/multicore':
                scheduler = MultiCoreScheduler()
                status, schedule = scheduler.multicore_core_scheduler(system)
            
            if status == 0:
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
        self.do_POST()


# LP Scheduler
def lpScheduler(system):
    # Determine the hyper-period of the tasks
    taskPeriods = [task['period'] for task in system['EntityStore']]
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
    
    # Last summation of task dependency delays
    lastDelays = -1

    # FIXME: Why do we even need to iterate?
    # Iterate through each dependency and try to tighten the task dependency delays
    for taskDependencyPair in taskDependenciesList:
        # Keep iterating LP solver until no further optimisations can be found
        lookingForBetterSolution = True
        
        # List of LP constraint used to tighten the current dependency
        delayVariablesToTighten = []

        
        while lookingForBetterSolution:
            print()
            print(f"Iteration {timesRan} ... {taskDependencyPair}")
            timesRan += 1
            if (system.get("CoreStore") is None or len(system.get("CoreStore")) ==0 ):
                system["CoreStore"] = [{'name': 'c1', 'speedup': 1}] #needed for old version of the exported file before multicore support
           
            # Create LP writer for the selected solver
            lp = PuLPWriter(Config.lpFile, Config.objectiveVariable, lpLargeConstant, Config.objectiveType)

            # Create the objective to minimize task dependency delay
            lp.writeObjective()

            # Equation 2
            # Encode the task instances over the scheduling window as LP constraints
            # Return all task instances within the scheduling window
            allTaskInstances = lp.createTaskInstancesAsConstraints(system, schedulingWindow, system.get("CoreStore"), Config)
            
            # Equation 3
            # Create constraints that ensures no two tasks overlap (Single Core)
            lp.createTaskExecutionConstraints(allTaskInstances.copy(), system.get("CoreStore"), Config)


            # Equations 4 and 5
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
            
            # Equation 6
            # Create objective equation has to be called after createTaskDependencyConstraints as the depenedency selection varaibles are needed to compute the summed end-to-end time
            lp.writeObjectiveEquation()
            
            # Call the LP solver
            results = {}
            
            lp.solve(Config.solverProg) 

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
                print(f"Current objective value: {results[Config.objectiveVariable]} ns")
                lastDelays = results[Config.objectiveVariable]
                # Create the task schedule that is encoded in the LP solution
                lastFeasibleSchedule = exportSchedule(system, lp, allTaskInstances, results, Config)

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
    print(f"Final objective value: {lastDelays} ns")
    return lp.prob.sol_status, lastFeasibleSchedule

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

def exportSchedule(system, lp, allTaskInstances, results, Config):
    schedule = {
        "EntityInstancesStore" : []
    }
    
    for task in system['EntityStore']:
        if (task['name'] == "__system"):
            continue
        initialOffset = 0
        if Config.useOffSet:
            initialOffset = float(results[lp.taskOffset(task['name'])])
            
        taskInstancesJson = {
            "name": task['name'],
            "initialOffset": initialOffset, #FIXME: when is this used in the GUI ?
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
            
            allocatedCore = None
            for c in system["CoreStore"]:
                if results[lp.taskInstCoreAllocation(lp.instVarName(task['name'],index), c["name"])] == 1:
                    allocatedCore = c
                    break
            if allocatedCore == None:
                print("Error task instance with no core allocation on export")
                print("Task: "+task['name'])
                print("Instance: "+instance)
                raise Exception("Error task instance with no core allocation on export. Task: "+task['name']+" Instance: "+instance)
            
            taskInstance = {
                "instance" : index,
                "periodStartTime" : index * period,
                "letStartTime" : startTime,
                "letEndTime" : endTime,
                "periodEndTime" : (index + 1) * period,
                "executionTime": task['wcet'],
                "executionIntervals": [ {
                    "startTime": startTime,
                    "endTime": startTime + math.ceil(wcet/allocatedCore["speedup"]),
                    "core" : allocatedCore["name"]
                } ],
                "currentCore": allocatedCore
            }
            taskInstancesJson['value'].append(taskInstance)
        schedule['EntityInstancesStore'].append(taskInstancesJson)
    return schedule




if __name__ == '__main__':
    avaliableSolvers = pl.listSolvers(onlyAvailable=True)
    print("LET-LP-Scheduler")
    print("----------------")
    print("Supported Solvers ['GLPK_CMD', 'PYGLPK', 'CPLEX_CMD', 'CPLEX_PY', 'CPLEX_DLL', 'GUROBI', 'GUROBI_CMD', 'MOSEK', 'XPRESS', 'PULP_CBC_CMD', 'COIN_CMD', 'COINMP_DLL', 'CHOCO_CMD', 'MIPCL_CMD', 'SCIP_CMD']")
    print("Avaliable Solver on this PC: "+str(avaliableSolvers))
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default="")
    parser.add_argument("--solver", choices=avaliableSolvers, type=str, required=True)
    args = parser.parse_args()
    
   # Set the OS and executable file suffix
    Config.os = sys.platform
    if Config.os == "win32":
        Config.exeSuffix = ".exe"
    
    # Set the LP solver
    if args.solver in avaliableSolvers:
        Config.solverProg = args.solver

    print(f"Solver: {Config.solverProg}")

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
    
