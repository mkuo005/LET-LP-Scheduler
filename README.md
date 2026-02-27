# LET-LP-Scheduler
Logical Execution Time Linear Programming Scheduler is an backend server for the following 
[LetSynchronise](https://github.com/uniba-swt/LetSynchronise) framework plugins:
* [`Minimise End-to-End Response Times (ILP)`](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.ilp.js):
  Minimises the delays of task dependencies in a LET system
* [`Minimise End-to-End Response Time (WCET, ILP)`](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.end2endMinMC.js):
  Minimises the communication delay in a System-Level LET system
* [`Minimise Core Usage (WCET)`](https://github.com/uniba-swt/LetSynchronise/blob/master/sources/plugins/ls.plugin.goal.minCoreUsage.js) 
  Minimises the number of cores needed by a System-Level LET system

Limitations:
* The task schedule is analysed over a scheduling window, starting at 0 ns and ending at the makespan, rounded up to the next hyper-period.
* Only minimises task dependency delays. This indirectly minimises the overall end-to-end response times of all event chains.
* Task dependencies are minimised in random order. No concept of priority or importance.
* Tasks are scheduled non-preemptively.

## Dependencies
* Python 3
* LetSynchronise framework
* Linear Programming (LP) solver: PuLP and all PuLP supported solvers 
  (Mosek (MOSEK), Gurobi (GUROBI), Cplex (CPLEX_PY), Xpress (XPRESS_PY), HiGHS (HiGHS), SCIP (SCIP_PY), XPRESS (XPRESS_PY), and COPT (COPT))

## Standalone Usage
1. Run main.py and it will list all avalaible solvers avaliable on the system
   * `python3 main.py`
   * Example result: `Avaliable Solver on this PC: ['GUROBI_CMD', 'PULP_CBC_CMD']`
2. Specify the LP solver (e.g., `PULP_CBC_CMD`), the LetSynchronise system model file (e.g., `system.json`), 
   and the optimisation goal (e.g., `min-core-usage`, `min-e2e-mc`, or `ilp`):
   * `python3 main.py --file system.json --solver PULP_CBC_CMD, --goal ilp` 

## LetSynchronise Plugin Usage
1. Run the LetSynchronise framework in a browser
2. Start up the server with selected solver:
   * PuLP: `python3 main.py --solver PULP_CBC_CMD` 
3. In the "Analyse" tab of LetSynchronise, under "LET Task Schedule", choose `No Scheduling (Identity)` 
   and `Minimise End-to-End Response Times (ILP)` or `Minimise End-to-End Response Time (WCET, ILP)`
   or `Minimise Core Usage (WCET, ILP)`
4. Set the `Makespan` of the generated schedule
5. Click the `Optimise` button

### Server Address
The LET-LP-Scheduler communicates with LetSynchronise via `localhost` on port `8181`. The address can be changed, but this has to be reflected in the address setup defined in the LetSynchronise framework plugins.

### Server Requests
The LET-LP-Scheduler uses POST requests to service a scheduling request. The body of a POST request contains a LetSynchronise system model in JSON format ([examples](https://github.com/uniba-swt/LetSynchronise/blob/master/examples)) and extended with `"PluginParameters": { "Makespan": <int> }` at the top level.
