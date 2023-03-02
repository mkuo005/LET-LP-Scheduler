# LET-LP-Scheduler
Logical Execution Time Linear Programming Scheduler is an external plugin for the [LetSynchronise](https://github.com/eyip002/LetSynchronise) framework that computes an optimal schedule for overall system end-to-end response times.  

## Dependencies
* Python 3
* LetSynchronise framework
* Linear Programming Solver ([Gurobi](https://www.gurobi.com/) or [LPSolve](https://lpsolve.sourceforge.net/5.5/))


## Usage
* Step 0 - Make sure python3 and Gurobi or LPSolve is in the system PATH variable
* Step 1 - Make sure LetSynchronise framework is running on a browser
* Step 2 (Gurobi) - `python3 main.py` 
  * Step 2a (LpSolve) - `python3 main.py -lpsolve` 
* Step 3 - In the Analyse tab of LetSynchronise framework choose Scheduler `No Scheduling (Identity)` and Goal `ILP-based Schedule Optimizer`
* Step 4 - Select the Makespan you would like to view the generated schedule
* Step 5 - Press the `AutoSync` button

### Ports 
The LET-LP-Scheduler communicates with LetSynchronise using localhost on port 8181. The ports can be changed, however, the same change will need to be reflect on the plugin in LetSynchronise.

### Server requests
The LET-LP-Scheduler uses post requests to service a scheduling request. The body of the post request is in the LetSynchronise JSON format ([examples](https://github.com/eyip002/LetSynchronise/tree/master/examples)) with the addition of the `"makespan" : int` at the top level.
