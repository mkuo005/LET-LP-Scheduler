from multicore import MultiCoreScheduler

system = {
"EntityStore": [
    {
      "name": "task_a",
      "type": "task",
      "priority": "null",
      "initialOffset": 0,
      "activationOffset": 200000,
      "duration": 4500000,
      "period": 5000000,
      "inputs": [
        "in"
      ],
      "outputs": [
        "out"
      ],
      "wcet": 3000000,
      "acet": 2500000,
      "bcet": 2000000,
      "distribution": "Normal",
      "core": "c1"
    },
    {
      "name": "task_b",
      "type": "task",
      "priority": 1,
      "initialOffset": 0,
      "activationOffset": 500000,
      "duration": 1000000,
      "period": 2000000,
      "inputs": [
        "in"
      ],
      "outputs": [
        "out"
      ],
      "wcet": 500000,
      "acet": 400000,
      "bcet": 300000,
      "distribution": "Uniform",
      "core": "c1"
    },
    {
      "name": "task_c",
      "type": "task",
      "priority": 3,
      "initialOffset": 750000,
      "activationOffset": 0,
      "duration": 400000,
      "period": 1000000,
      "inputs": [
        "in1",
        "in2"
      ],
      "outputs": [
        "out"
      ],
      "wcet": 250000,
      "acet": 175000,
      "bcet": 100000,
      "distribution": "Weibull",
      "core": "c2"
    }
  ],

  "EntityInstancesStore": [
    {
      "name": "task_a",
      "type": "task",
      "initialOffset": 0,
      "value": [
        {
          "instance": 0,
          "periodStartTime": 0,
          "letStartTime": 200000,
          "letEndTime": 4700000,
          "periodEndTime": 5000000,
          "executionTime": 2000000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 1,
          "periodStartTime": 5000000,
          "letStartTime": 5200000,
          "letEndTime": 9700000,
          "periodEndTime": 10000000,
          "executionTime": 2000000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
      ],
      "executionTiming": "BCET"
    },
    {
      "name": "task_b",
      "type": "task",
      "initialOffset": 0,
      "value": [
        {
          "instance": 0,
          "periodStartTime": 0,
          "letStartTime": 500000,
          "letEndTime": 1500000,
          "periodEndTime": 2000000,
          "executionTime": 300000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 1,
          "periodStartTime": 2000000,
          "letStartTime": 2500000,
          "letEndTime": 3500000,
          "periodEndTime": 4000000,
          "executionTime": 300000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 2,
          "periodStartTime": 4000000,
          "letStartTime": 4500000,
          "letEndTime": 5500000,
          "periodEndTime": 6000000,
          "executionTime": 300000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 3,
          "periodStartTime": 6000000,
          "letStartTime": 6500000,
          "letEndTime": 7500000,
          "periodEndTime": 8000000,
          "executionTime": 300000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 4,
          "periodStartTime": 8000000,
          "letStartTime": 8500000,
          "letEndTime": 9500000,
          "periodEndTime": 10000000,
          "executionTime": 300000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
      ],
      "executionTiming": "BCET"
    },
    {
      "name": "task_c",
      "type": "task",
      "initialOffset": 750000,
      "value": [
        {
          "instance": 0,
          "periodStartTime": 750000,
          "letStartTime": 750000,
          "letEndTime": 1150000,
          "periodEndTime": 1750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 1,
          "periodStartTime": 1750000,
          "letStartTime": 1750000,
          "letEndTime": 2150000,
          "periodEndTime": 2750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 2,
          "periodStartTime": 2750000,
          "letStartTime": 2750000,
          "letEndTime": 3150000,
          "periodEndTime": 3750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 3,
          "periodStartTime": 3750000,
          "letStartTime": 3750000,
          "letEndTime": 4150000,
          "periodEndTime": 4750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 4,
          "periodStartTime": 4750000,
          "letStartTime": 4750000,
          "letEndTime": 5150000,
          "periodEndTime": 5750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 5,
          "periodStartTime": 5750000,
          "letStartTime": 5750000,
          "letEndTime": 6150000,
          "periodEndTime": 6750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 6,
          "periodStartTime": 6750000,
          "letStartTime": 6750000,
          "letEndTime": 7150000,
          "periodEndTime": 7750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 7,
          "periodStartTime": 7750000,
          "letStartTime": 7750000,
          "letEndTime": 8150000,
          "periodEndTime": 8750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 8,
          "periodStartTime": 8750000,
          "letStartTime": 8750000,
          "letEndTime": 9150000,
          "periodEndTime": 9750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
        {
          "instance": 9,
          "periodStartTime": 9750000,
          "letStartTime": 9750000,
          "letEndTime": 10150000,
          "periodEndTime": 10750000,
          "executionTime": 100000,
          "executionIntervals": [],
          "currentCore": "Default",
          "remainingExecutionTime": 0
        },
      ],
      "executionTiming": "BCET"
    }
  ],
"CoreStore": [
    {
      "name": "c1",
      "speedup": 1,
      "device": "d1"
    },
    {
      "name": "c2",
      "speedup": 1,
      "device": "d2"
    },
    {
      "name": "c3",
      "speedup": 1,
      "device": "d2"
    },
    # {
    #   "name": "c4",
    #   "speedup": 1,
    #   "device": "d1"
    # }
  ],
"DeviceStore": [
    {
      "name": "d1",
      "speedup": 1,
      "delays": [
        {
          "protocol": "tcp",
          "bcdt": 200000,
          "acdt": 500000,
          "wcdt": 800000,
          "distribution": "Normal"
        }
      ]
    },
    {
      "name": "d2",
      "speedup": 1,
      "delays": [
        {
          "protocol": "tcp",
          "bcdt": 200000,
          "acdt": 500000,
          "wcdt": 800000,
          "distribution": "Normal"
        }
      ]
    }
  ],
  "DependencyStore": [
    {
      "name": "a",
      "source": {
        "task": "__system",
        "port": "SystemInput"
      },
      "destination": {
        "task": "task_a",
        "port": "in"
      }
    },
    {
      "name": "b",
      "source": {
        "task": "task_a",
        "port": "out"
      },
      "destination": {
        "task": "task_b",
        "port": "in"
      }
    },
        {
      "name": "c",
      "source": {
        "task": "task_b",
        "port": "out"
      },
      "destination": {
        "task": "task_c",
        "port": "in"
      }
    }
  ],
  "DeviceStore": [
    {
      "name": "d1",
      "speedup": 1,
      "delays": [
        {
          "protocol": "tcp",
          "bcdt": 200000,
          "acdt": 500000,
          "wcdt": 800000,
          "distribution": "Normal"
        }
      ]
    },
    {
      "name": "d2",
      "speedup": 1,
      "delays": [
        {
          "protocol": "tcp",
          "bcdt": 200000,
          "acdt": 500000,
          "wcdt": 800000,
          "distribution": "Normal"
        }
      ]
    }
  ],
   "NetworkDelayStore": [
    {
      "name": "d1-to-d2",
      "source": "d1",
      "dest": "d2",
      "bcdt": 300000,
      "acdt": 400000,
      "wcdt": 500000,
      "distribution": "Normal"
    },
    {
      "name": "d2-to-d1",
      "source": "d2",
      "dest": "d1",
      "bcdt": 300000,
      "acdt": 400000,
      "wcdt": 500000,
      "distribution": "Normal"
    }
  ],
  "EventChainStore": [
    {
      "segment": {
        "name": "a",
        "source": {
          "task": "task_a",
          "port": "out"
        },
        "destination": {
          "task": "task_b",
          "port": "in"
        }
      },
      "name": "a1",
      "successor": {
        "segment": {
          "name": "b",
          "source": {
            "task": "task_b",
            "port": "out"
          },
          "destination": {
            "task": "task_c",
            "port": "in1"
          }
        }
      }
    }
  ],
"PluginParameters": {"Makespan": 11000000},
}

scheduler = MultiCoreScheduler()
scheduler.multicore_core_scheduler(system)