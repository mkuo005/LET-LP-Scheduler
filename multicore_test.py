from multicore import MultiCoreScheduler

system = {
 "ConstraintInstancesStore": [],
  "ConstraintStore": [
    {
      "name": "TestConstraint1",
      "eventChain": "Test",
      "relation": "<",
      "time": 3000000
    },
    {
      "name": "TestConstraint2",
      "eventChain": "Test",
      "relation": "<",
      "time": 3000000
    },
    {
      "name": "TimingConstraint1",
      "eventChain": "EventChain1",
      "relation": "<=",
      "time": 4000000
    },
    {
      "name": "TimingConstraint2",
      "eventChain": "EventChain2",
      "relation": "<=",
      "time": 5000000
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
    }
  ],
  "DependencyInstancesStore": [
    {
      "name": "alpha",
      "value": [
        {
          "instance": 0,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 0,
            "timestamp": 0
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 0,
            "timestamp": 0
          }
        },
        {
          "instance": 1,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 1,
            "timestamp": 3000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 1,
            "timestamp": 3000000
          }
        },
        {
          "instance": 2,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 2,
            "timestamp": 6000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 2,
            "timestamp": 6000000
          }
        },
        {
          "instance": 3,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 3,
            "timestamp": 9000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 3,
            "timestamp": 9000000
          }
        },
        {
          "instance": 4,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 4,
            "timestamp": 12000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 4,
            "timestamp": 12000000
          }
        },
        {
          "instance": 5,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 5,
            "timestamp": 15000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 5,
            "timestamp": 15000000
          }
        },
        {
          "instance": 6,
          "receiveEvent": {
            "entity": "task_a",
            "port": "in",
            "entityInstance": 6,
            "timestamp": 18000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 6,
            "timestamp": 18000000
          }
        }
      ]
    },
    {
      "name": "beta",
      "value": [
        {
          "instance": 0,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 1,
            "timestamp": 2000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 0,
            "timestamp": 2000000
          }
        },
        {
          "instance": 1,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 2,
            "timestamp": 4000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 0,
            "timestamp": 2000000
          }
        },
        {
          "instance": 2,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 3,
            "timestamp": 6000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 1,
            "timestamp": 5000000
          }
        },
        {
          "instance": 3,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 4,
            "timestamp": 8000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 2,
            "timestamp": 8000000
          }
        },
        {
          "instance": 4,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 5,
            "timestamp": 10000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 2,
            "timestamp": 8000000
          }
        },
        {
          "instance": 5,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 6,
            "timestamp": 12000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 3,
            "timestamp": 11000000
          }
        },
        {
          "instance": 6,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 7,
            "timestamp": 14000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 4,
            "timestamp": 14000000
          }
        },
        {
          "instance": 7,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 8,
            "timestamp": 16000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 4,
            "timestamp": 14000000
          }
        },
        {
          "instance": 8,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in1",
            "entityInstance": 9,
            "timestamp": 18000000
          },
          "sendEvent": {
            "entity": "task_a",
            "port": "out",
            "entityInstance": 5,
            "timestamp": 17000000
          }
        }
      ]
    },
    {
      "name": "delta",
      "value": [
        {
          "instance": 0,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 0,
            "timestamp": 1000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 0,
            "timestamp": 1000000
          }
        },
        {
          "instance": 1,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 1,
            "timestamp": 3000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 1,
            "timestamp": 3000000
          }
        },
        {
          "instance": 2,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 2,
            "timestamp": 5000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 2,
            "timestamp": 5000000
          }
        },
        {
          "instance": 3,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 3,
            "timestamp": 7000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 3,
            "timestamp": 7000000
          }
        },
        {
          "instance": 4,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 4,
            "timestamp": 9000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 4,
            "timestamp": 9000000
          }
        },
        {
          "instance": 5,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 5,
            "timestamp": 11000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 5,
            "timestamp": 11000000
          }
        },
        {
          "instance": 6,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 6,
            "timestamp": 13000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 6,
            "timestamp": 13000000
          }
        },
        {
          "instance": 7,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 7,
            "timestamp": 15000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 7,
            "timestamp": 15000000
          }
        },
        {
          "instance": 8,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 8,
            "timestamp": 17000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 8,
            "timestamp": 17000000
          }
        },
        {
          "instance": 9,
          "receiveEvent": {
            "entity": "__system",
            "port": "SystemOutput",
            "entityInstance": 9,
            "timestamp": 19000000
          },
          "sendEvent": {
            "entity": "task_c",
            "port": "out",
            "entityInstance": 9,
            "timestamp": 19000000
          }
        }
      ]
    },
    {
      "name": "gamma",
      "value": [
        {
          "instance": 0,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 1,
            "timestamp": 2000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 0,
            "timestamp": 1000000
          }
        },
        {
          "instance": 1,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 2,
            "timestamp": 4000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 1,
            "timestamp": 3000000
          }
        },
        {
          "instance": 2,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 3,
            "timestamp": 6000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 2,
            "timestamp": 5000000
          }
        },
        {
          "instance": 3,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 4,
            "timestamp": 8000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 3,
            "timestamp": 7000000
          }
        },
        {
          "instance": 4,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 5,
            "timestamp": 10000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 4,
            "timestamp": 9000000
          }
        },
        {
          "instance": 5,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 6,
            "timestamp": 12000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 5,
            "timestamp": 11000000
          }
        },
        {
          "instance": 6,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 7,
            "timestamp": 14000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 6,
            "timestamp": 13000000
          }
        },
        {
          "instance": 7,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 8,
            "timestamp": 16000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 7,
            "timestamp": 15000000
          }
        },
        {
          "instance": 8,
          "receiveEvent": {
            "entity": "task_c",
            "port": "in2",
            "entityInstance": 9,
            "timestamp": 18000000
          },
          "sendEvent": {
            "entity": "task_b",
            "port": "out",
            "entityInstance": 8,
            "timestamp": 17000000
          }
        }
      ]
    },
    {
      "name": "theta",
      "value": [
        {
          "instance": 0,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 0,
            "timestamp": 0
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 0,
            "timestamp": 0
          }
        },
        {
          "instance": 1,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 1,
            "timestamp": 2000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 1,
            "timestamp": 2000000
          }
        },
        {
          "instance": 2,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 2,
            "timestamp": 4000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 2,
            "timestamp": 4000000
          }
        },
        {
          "instance": 3,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 3,
            "timestamp": 6000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 3,
            "timestamp": 6000000
          }
        },
        {
          "instance": 4,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 4,
            "timestamp": 8000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 4,
            "timestamp": 8000000
          }
        },
        {
          "instance": 5,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 5,
            "timestamp": 10000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 5,
            "timestamp": 10000000
          }
        },
        {
          "instance": 6,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 6,
            "timestamp": 12000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 6,
            "timestamp": 12000000
          }
        },
        {
          "instance": 7,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 7,
            "timestamp": 14000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 7,
            "timestamp": 14000000
          }
        },
        {
          "instance": 8,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 8,
            "timestamp": 16000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 8,
            "timestamp": 16000000
          }
        },
        {
          "instance": 9,
          "receiveEvent": {
            "entity": "task_b",
            "port": "in",
            "entityInstance": 9,
            "timestamp": 18000000
          },
          "sendEvent": {
            "entity": "__system",
            "port": "SystemInput",
            "entityInstance": 9,
            "timestamp": 18000000
          }
        }
      ]
    }
  ],
  "DependencyStore": [
    {
      "name": "beta",
      "source": {
        "entity": "task_a",
        "port": "out"
      },
      "destination": {
        "entity": "task_b",
        "port": "in1"
      }
    },
  ],
  "DeviceStore": [
    {
      "name": "d1",
      "speedup": 1,
      "delays":
        {
          "tcp":
           {
            "bcdt": 200000,
            "acdt": 300000,
            "wcdt": 400000,
            "distribution": "Normal"               
           }
        }
    },
    {
      "name": "d2",
      "speedup": 1,
      "delays": 
        {
          "tcp":
          {
            "bcdt": 200000,
            "acdt": 300000,
            "wcdt": 400000,
            "distribution": "Normal"   
          }
        }
      
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
          "periodEndTime": 3000000,
          "letStartTime": 0,
          "letEndTime": 2000000,
          "executionTime": 500000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 500000,
              "startTime": 0
            }
          ]
        },
        {
          "instance": 1,
          "periodStartTime": 3000000,
          "periodEndTime": 6000000,
          "letStartTime": 3000000,
          "letEndTime": 5000000,
          "executionTime": 500000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 3500000,
              "startTime": 3000000
            }
          ]
        },
        {
          "instance": 2,
          "periodStartTime": 6000000,
          "periodEndTime": 9000000,
          "letStartTime": 6000000,
          "letEndTime": 8000000,
          "executionTime": 500000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 6500000,
              "startTime": 6000000
            }
          ]
        },
      ]
    },
    {
      "name": "task_b",
      "type": "task",
      "initialOffset": 0,
      "value": [
        {
          "instance": 0,
          "periodStartTime": 0,
          "periodEndTime": 2000000,
          "letStartTime": 0,
          "letEndTime": 1000000,
          "executionTime": 400000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 1000000,
              "startTime": 600000
            }
          ]
        },
        {
          "instance": 1,
          "periodStartTime": 2000000,
          "periodEndTime": 4000000,
          "letStartTime": 2000000,
          "letEndTime": 3000000,
          "executionTime": 400000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 2400000,
              "startTime": 2000000
            }
          ]
        },
        {
          "instance": 2,
          "periodStartTime": 4000000,
          "periodEndTime": 6000000,
          "letStartTime": 4000000,
          "letEndTime": 5000000,
          "executionTime": 400000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 4400000,
              "startTime": 4000000
            }
          ]
        },
        {
          "instance": 3,
          "periodStartTime": 6000000,
          "periodEndTime": 8000000,
          "letStartTime": 6000000,
          "letEndTime": 7000000,
          "executionTime": 400000,
          "currentCore": {
            "name": "c2",
            "speedup": 1,
            "device": "d2",
            "id": 1
          },
          "executionIntervals": [
            {
              "core": "c2",
              "endTime": 6900000,
              "startTime": 6500000
            }
          ]
        },
      ]
    },
  ],
  "EntityStore": [
    {
      "name": "task_a",
      "type": "task",
      "initialOffset": 0,
      "activationOffset": 0,
      "duration": 2000000,
      "period": 3000000,
      "inputs": [
        "in"
      ],
      "outputs": [
        "out"
      ],
      "wcet": 500000,
      "acet": 500000,
      "bcet": 500000,
      "distribution": "Normal",
      "core": "c1"
    },
    {
      "name": "task_b",
      "type": "task",
      "initialOffset": 0,
      "activationOffset": 0,
      "duration": 1000000,
      "period": 2000000,
      "inputs": [
        "in"
      ],
      "outputs": [
        "out"
      ],
      "wcet": 400000,
      "acet": 400000,
      "bcet": 400000,
      "distribution": "Uniform"
    },
  ],
  "EventChainInstanceStore": [],
  "EventChainStore": [
    {
      "segment": {
        "name": "alpha",
        "source": {
          "entity": "__system",
          "port": "SystemInput"
        },
        "destination": {
          "entity": "task_a",
          "port": "in"
        }
      },
      "name": "EventChain1",
      "successor": {
        "segment": {
          "name": "beta",
          "source": {
            "entity": "task_a",
            "port": "out"
          },
          "destination": {
            "entity": "task_c",
            "port": "in1"
          }
        },
        "successor": {
          "segment": {
            "name": "delta",
            "source": {
              "entity": "task_c",
              "port": "out"
            },
            "destination": {
              "entity": "__system",
              "port": "SystemOutput"
            }
          }
        }
      }
    },
    {
      "segment": {
        "name": "theta",
        "source": {
          "entity": "__system",
          "port": "SystemInput"
        },
        "destination": {
          "entity": "task_b",
          "port": "in"
        }
      },
      "name": "EventChain2",
      "successor": {
        "segment": {
          "name": "gamma",
          "source": {
            "entity": "task_b",
            "port": "out"
          },
          "destination": {
            "entity": "task_c",
            "port": "in2"
          }
        },
        "successor": {
          "segment": {
            "name": "delta",
            "source": {
              "entity": "task_c",
              "port": "out"
            },
            "destination": {
              "entity": "__system",
              "port": "SystemOutput"
            }
          }
        }
      }
    },
    {
      "segment": {
        "name": "gamma",
        "source": {
          "entity": "task_b",
          "port": "out"
        },
        "destination": {
          "entity": "task_c",
          "port": "in2"
        }
      },
      "name": "Test"
    }
  ],
  "MemoryStore": [],
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
  "SystemInputStore": [
    {
      "name": "SystemInput"
    }
  ],
  "SystemOutputStore": [
    {
      "name": "SystemOutput"
    }
  ],
  "PluginParameters": {"Makespan": 6000000},
}

scheduler = MultiCoreScheduler()
scheduler.multicore_core_scheduler(system, "/min-e2e-mc")