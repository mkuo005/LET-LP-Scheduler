from enum import Enum

class GenericConstraint():

    class lpoperator(Enum):
        EQUAL = 0
        GREATERTHAN = 1
        GREATEROREQUAL = 2
        LESSTHAN = 3
        LESSOREQUAL = 4


    this.inequalityoperator = lpoperator.EQUAL
    this.variable = ""
    this.