# LET-LP-Scheduler
Logical Execution Time Linear Programming Scheduler is an [external plugin](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.ilp.js) for the [LetSynchronise](https://github.com/uniba-swt/LetSynchronise) framework that minimises the delays of task dependencies.  

Limitations:
* The task schedule is analysed over a scheduling window, starting at 0 ns and ending at the makespan, rounded up to the next hyper-period.
* Only minimises task dependency delays. This indirectly minimises the overall end-to-end response times of all event chains.
* Task dependencies are minimised in random order. No concept of priority or importance.
* Tasks are scheduled non-preemptively.
* Tasks are scheduled for execution on a single-core processor.

## Dependencies
* Python 3
* LetSynchronise framework
* Linear Programming (LP) solver: PuLP and all PuLP supported solvers (Mosek (MOSEK), Gurobi (GUROBI), Cplex (CPLEX_PY), Xpress (XPRESS_PY), HiGHS (HiGHS), SCIP (SCIP_PY), XPRESS (XPRESS_PY), and COPT (COPT))

## Standalone Usage
1. Run main.py and it will list all avalaible solvers avaliable on the system
   * `python3 main.py`
   * Example result: `Avaliable Solver on this PC: ['GUROBI_CMD', 'PULP_CBC_CMD']`
2. Specify the LP solver and LetSynchronise system model file (e.g., `system.json`):
   * PuLP: `python3 main.py --file system.json --solver PULP_CBC_CMD` 

## LetSynchronise Plugin Usage
1. Run the LetSynchronise framework in a browser
2. Start up the server with selected solver:
   * PuLP: `python3 main.py --solver PULP_CBC_CMD` 
3. In the "Analyse" tab of LetSynchronise, under "LET Task Schedule", choose `No Scheduling (Identity)` and `Minimise End-to-End Response Times (ILP, Single Core)`
4. Set the `Makespan` of the generated schedule
5. Click the `Optimise` button

### Server Address
The LET-LP-Scheduler communicates with LetSynchronise via `localhost` on port `8181`. The address can be changed, but this has to be reflect in the address setup defined in the LetSynchronise plugin [`ls.plugin.goal.ilp.js`](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.ilp.js).

### Server Requests
The LET-LP-Scheduler uses post requests to service a scheduling request. The body of a post request contains a LetSynchronise system model in JSON format ([examples](https://github.com/uniba-swt/LetSynchronise/blob/master/examples)) with `'Makespan' : int` at the top level.
