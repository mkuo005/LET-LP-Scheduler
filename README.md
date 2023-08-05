# LET-LP-Scheduler
Logical Execution Time Linear Programming Scheduler is an [external plugin](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.ilp.js) for the [LetSynchronise](https://github.com/uniba-swt/LetSynchronise) framework that minimises the delays of task dependencies.  

Limitations:
* The task schedule is analysed over a scheduling window, starting at 0 ns and ending at the makespan, rounded up to the next hyper-period. End-to-end constraints where none of their instances appears within the scheduling window are not optimised.
* Can only indirectly minimise the overall end-to-end response times of all event chains.

## Dependencies
* Python 3
* LetSynchronise framework
* Linear Programming (LP) solver: [Gurobi](https://www.gurobi.com/) or [LpSolve](https://lpsolve.sourceforge.net/5.5/)

## Standalone Usage
1. Make sure python3 and Gurobi or LpSolve are in the system PATH variable
2. Specify the LP solver and LetSynchronise system model file (e.g., `system.json`):
   * Gurobi: `python3 main.py --file system.json --solver gurobi` 
   * LpSolve: `python3 main.py --file system.json --solver lpsolve` 

## LetSynchronise Plugin Usage
1. Make sure python3 and Gurobi or LpSolve are in the system PATH variable
2. Run the LetSynchronise framework in a browser
3. Start up the server:
   * Gurobi: `python3 main.py --solver gurobi` 
   * LpSolve: `python3 main.py --solver lpsolve` 
4. In the "Analyse" tab of LetSynchronise, under "LET Task Schedule", choose `No Scheduling (Identity)` and `Minimise End-to-End Response Times (ILP, Single Core)`
5. Set the `Makespan` of the generated schedule
6. Click the `Optimise` button

### Server Address
The LET-LP-Scheduler communicates with LetSynchronise via `localhost` on port `8181`. The address can be changed, but this has to be reflect in the address setup defined in the LetSynchronise plugin [`ls.plugin.goal.ilp.js`](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.ilp.js).

### Server Requests
The LET-LP-Scheduler uses post requests to service a scheduling request. The body of a post request contains a LetSynchronise system model in JSON format ([examples](https://github.com/uniba-swt/LetSynchronise/blob/master/examples)) with `'Makespan' : int` at the top level.
