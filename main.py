#Webserver API
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer # python3
import socketserver 
import time

import argparse
import json
import math
import subprocess
import re

class server(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
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
        print(post_body)
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

def lpScheduler(system):
    
    #export schedule
    schedule = {
        "DependencyInstancesStore" : [], 
        "EventChainInstanceStore" : [],
        "TaskInstancesStore" : []
        }
    lastFeasibleSchedule = schedule.copy()
    limitEndtoEndConstraint = {}
    hyperperiod = 1
    for t in system['TaskStore']:
        hyperperiod = math.lcm(hyperperiod, t['period'])
    print(hyperperiod)
    reductionList = []
    hyperperiodMultiplier = 1
    hyperperiod = hyperperiod * hyperperiodMultiplier
    veryLargeNumber = hyperperiod
    for dep in system['DependencyStore']:
            name = dep['name']
            srcTask = dep['source']['task']
            destTask = dep['destination']['task']
            if (srcTask == '__system' or destTask == '__system'):
                continue
            reductionList.append(srcTask+"-"+destTask)
    
    for reduction in reductionList:
        lookingForOptimalSolution = True
        constraintReductionList = []
        while(lookingForOptimalSolution):
            lp = open("system.lp", "w")
            lp.write("min: endToEndTime;\n")
            booleanVariables = []
            intVaraibles = []
            allTaskInstances = {}
            taskWCET = {}
            taskPeriod = {}
            for t in system['TaskStore']:
                lp.write("\n/* task properties */\n")
                task = t['name']
                wcet = t['wcet']
                period = t['period']
                taskWCET[task] = wcet
                taskPeriod[task] = period
                lp.write(task + "_wcet = "+ str(wcet) + ";\n")
                instances = []
                i = 0
                
                for x in range(0, hyperperiod, period):
                    inst = task + "_" + str(i)
                    instances.append(inst)
                    lp.write(inst + "_period_start_time = "+ str(x) + ";\n")
                    lp.write(inst + "_deadline = "+ str(x+period) + ";\n")

                    #task have to start after the period
                    lp.write("U"+inst + "_start_time >= "+ inst + "_period_start_time" + ";\n")

                    #task have to end before the period
                    lp.write("U"+inst + "_end_time <= "+ inst + "_deadline" + ";\n")

                    #task execution need to be larger than wcet
                    lp.write("U"+inst + "_end_time - "+ "U"+inst + "_start_time >= " + task + "_wcet;\n")
                    intVaraibles.append("U"+inst + "_end_time")
                    intVaraibles.append("U"+inst + "_start_time")
                    #all instances at most execute once
                    #lp.write(inst + " = 1;\n")
                    i = i + 1
                allTaskInstances[task] = instances
            
            print("Instances: " + str(allTaskInstances))
            copyAllTaskInstances = allTaskInstances.copy()
            #sumOfEndTimeString = ""
            #commutativeEndtime = 0
            lp.write("\n/* Make sure tasks do not overlap in execution */\n")
            for t in system['TaskStore']:
                wcet = t['wcet']
                instances = copyAllTaskInstances.pop(t['name'])
                #if (len(allTaskInstances) == 0):
                #    break #skip last task
                print(instances)
                for inst in instances:
                    #sumOfEndTimeString = sumOfEndTimeString + "+ "+ "U"+inst+"_end_time "
                    #commutativeEndtime = commutativeEndtime*2 + wcet
                    for key in copyAllTaskInstances.keys():
                        for other in copyAllTaskInstances[key]:
                            print(inst + " -> "+other)
                            controlVariable = "control"+inst+"_"+other
                            booleanVariables.append(controlVariable)
                            #beforeVariable = "before_"+inst+"_"+other
                            #afterVariable = "after_"+inst+"_"+other
                            #booleanVariables.append(beforeVariable)
                            #booleanVariables.append(afterVariable)
                            #lp.write(inst+"_end_time "+beforeVariable+" <= "+other+"_start_time "+beforeVariable+";\n")
                            #lp.write(inst+"_start_time "+afterVariable+" >= "+other+"_end_time "+afterVariable+";\n")
                            lp.write("U"+inst+"_end_time - " + "U"+other+"_start_time" +" <= "+str(veryLargeNumber) + " " + controlVariable + ";\n")
                            lp.write("U"+other+"_end_time - " + "U"+inst+"_start_time" +" <= "+str(veryLargeNumber) + " - " + str(veryLargeNumber) + " " + controlVariable + ";\n")
                            
                            #lp.write(inst+"_start_time "+" >= "+other+"_start_time "+";\n")
                            #lp.write(other+"_start_time "+" >= "+inst+"_start_time "+";\n")

            endToEndTime = ""
            lp.write("/* Each destination task instance of an event chain can only be connected to one source */\n")
            i = 0
            objectives = ""
            endToEndTaskTable = {}
            for dep in system['DependencyStore']:
                name = dep['name']
                srcTask = dep['source']['task']
                destTask = dep['destination']['task']
                if (srcTask == '__system' or destTask == '__system'):
                    continue
                srcTaskInstances = allTaskInstances[srcTask]
                destTaskInstances = allTaskInstances[destTask]
                lp.write("/* " + name + " */\n")

                endToEndTaskTable[srcTask+"-"+destTask] = []
                
                #Each event chain can only have 1 source task
                for destInst in destTaskInstances:
                    srcInstString = ""
                    first = True
                    
                    for srcInst in srcTaskInstances:
                        instanceConnection = "DEP_dest_"+destInst+"_src_"+srcInst
                        if (first):
                            srcInstString += instanceConnection
                            first = False
                        else:
                            srcInstString += " + " + instanceConnection
                        
                        #instance connection is only vaild if the source task finsihes before the destination task start time or else it must be zero
                        #The constaint should be 1 when the start_time is larger than the end_time therefore a -ve value or 0
                        lp.write("U"+srcInst+"_end_time" + " - " + "U"+destInst+"_start_time"+ " <= " + str(veryLargeNumber) + " - " +str(veryLargeNumber) +" "+ instanceConnection +";\n")

                        booleanVariables.append(instanceConnection)
                        if (len(endToEndTime) > 0):
                            endToEndTime += " + "
                        
                        #representation of instanceConnection + " " +"(U"+destInst+"_end_time - "+"U"+srcInst+"_start_time"+")"
                        #endToEndTime += instanceConnection + " " +"U"+destInst+"_end_time - "+instanceConnection + " U"+srcInst+"_start_time"+""
                        destInstNumber = int(destInst.split("_")[len(destInst.split("_"))-1])
                        srcInstNumber = int(srcInst.split("_")[len(srcInst.split("_"))-1])
                        print(destInstNumber)
                        print(srcInstNumber)
                        totalWCET = taskPeriod[srcTask]*(len(srcTaskInstances)-srcInstNumber+1)
                        #objectives += "E"+ str(i) + " = "+str(totalWCET)+" " + instanceConnection +";\n"
                        objectives += "EtoE"+ str(i) + " >= 0;\n"
                        X ="U"+destInst+"_end_time - " + " U"+srcInst+"_start_time"
                        objectives += X +" - "+str(veryLargeNumber)+" + "+str(veryLargeNumber)+" " +instanceConnection + " <= " + "EtoE"+ str(i) +";\n"
                        objectives += "EtoE"+ str(i) + " <= "+X+" + "+str(veryLargeNumber)+" - "+str(veryLargeNumber)+" " +instanceConnection +";\n"
                        
                        #a simple sum of the difference will be optimising the average - need to think...
                        endToEndTime += "EtoE"+ str(i)
                        endToEndTaskTable[srcTask+"-"+destTask].append("EtoE"+ str(i))
                        i = i + 1

                        
                    #The selected start time of the source instance plus the end time of the destination instance is the end-to-end delay for that chain.
                    lp.write(srcInstString+" = 1;\n")
                print(dep)
            
            for key in limitEndtoEndConstraint:
                if (key in constraintReductionList):
                    lp.write(key + "<=" + str(limitEndtoEndConstraint[key]-1) + ";\n")
                else:
                    lp.write(key + "<=" + str(limitEndtoEndConstraint[key]) + ";\n")

            lp.write(objectives)

            lp.write("endToEndTime = "+endToEndTime+";\n")
            #lp.write(sumOfEndTimeString + " = "+ str(commutativeEndtime) +";\n")
            for b in booleanVariables:
                lp.write("bin "+ b + ";\n")

            #ILP problem becomes very hard if large integer is used.
            #for i in intVaraibles:
            #    lp.write("int "+ i + ";\n")


            lp.close()
            results = {}

            with subprocess.Popen(["lp_solve_5.5.2.11_exe_win64\lp_solve.exe",'system.lp','-ip'], stdout=subprocess.PIPE) as proc:
                output = proc.stdout.read().decode("utf-8") 
                lines = output.split("\r\n")
                for l in lines:
                    if (len(l) == 0):
                        continue
                    fragment = re.split('\s+', l)
                    results[fragment[0]] = fragment[1]
            print("\nResults:\n---")
            
            if ("This problem is infeasible" in lines[0]):
                print("Problem not feasible.")
                lookingForOptimalSolution = False
                limitEndtoEndConstraint = {}
            else:
                print(results)
                for tasks in allTaskInstances.keys():
                    instances = allTaskInstances[tasks]
                    for inst in instances:
                        startTimeKey = "U"+inst+"_start_time"
                        print(inst+" start time," + results[startTimeKey])
                        endTimeKey = "U"+inst+"_end_time"
                        print(inst+" end time," + results[endTimeKey])
                for key in results.keys():
                    if ("DEP" in key):
                        destTaskInst = key[(key.find("_dest_")+len("_dest_")):key.find("_src_")]
                        srcTaskInst = key[key.find("_src_")+len("_src_"):len(key)]
                        print(srcTaskInst+"->"+destTaskInst + " : "+results[key])

                currentWorstChainTimes = {}
                for chain in endToEndTaskTable.keys():
                    constraints = endToEndTaskTable[chain]
                    for key in results.keys():
                        if ("EtoE" in key):
                            if key in constraints:
                                if ((chain in currentWorstChainTimes.keys()) == True):
                                    if(currentWorstChainTimes[chain] <  float(results[key])):
                                        currentWorstChainTimes[chain] = float(results[key])
                                else:
                                    currentWorstChainTimes[chain] =  float(results[key])
                                    
                print("Worst Case Chain Times:")
                print(endToEndTaskTable)
                print(currentWorstChainTimes)

                for key in results.keys():
                    if ("EtoE" in key):
                        print(key + " : "+results[key])

                constraintReductionList = []
                for chain in endToEndTaskTable.keys():  
                    constraints = endToEndTaskTable[chain]
                    for c in constraints:
                        limitEndtoEndConstraint[c] = round(currentWorstChainTimes[chain])
                        if (chain == reduction):
                            constraintReductionList.append(c)

                        
                
                for t in system['TaskStore']:
                    if (t['name']== "__system"):
                        continue
                    taskInstancesJson = {
                        "name" : t["name"],
                        "initialOffset" : 0,
                    }
                    instances = allTaskInstances[t['name']]
                    print (instances)
                    instancesLS = []
                    i = 0 
                    for inst in instances: 
                        print (inst)
                        print ("instances "+inst)
                        
                        startTimeKey = "U"+inst+"_start_time"
                        endTimeKey = "U"+inst+"_end_time"
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
                print(schedule)
                lastFeasibleSchedule = schedule.copy()
    return lastFeasibleSchedule



if __name__ == '__main__':
    print("Start LP Scheduler")
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", type=str, default="")
    args = parser.parse_args()
    if len(args.f) > 0:
        f = open(args.f)
        system = json.load(f)
        lpScheduler(system)
    else:
        hostName = "localhost"
        serverPort = 8080
        webServer = ThreadingHTTPServer((hostName, serverPort), server)
        print("Server started http://%s:%s" % (hostName, serverPort))

        try:
            webServer.serve_forever()
        except KeyboardInterrupt:
            pass
            
        webServer.server_close()
        print("Server stopped.")
    