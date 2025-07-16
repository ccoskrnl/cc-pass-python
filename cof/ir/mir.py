from typing import List, Dict, Union, Optional, Tuple

class Type:
    """Type system"""
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name

VOID = Type("void")
INT = Type("i32")
FLOAT = Type("f64")
BOOL = Type("bool")
PTR = Type("ptr")

class Value:
    def __init__(self, t: Type):
        self.type = t
        self.uses: List['Instruction'] = []

    def add_use(self, inst: 'Instruction'):
        self.uses.append(inst)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.type})"

class Temporary(Value):
    _counter = 0
    def __init__(self, t: Type):
        super().__init__(t)
        Temporary._counter += 1
        self.id = Temporary._counter

    def __repr__(self):
        return f"%{self.id}"

class Instruction:
    def __init__(self, opcode: str, result: Optional[Temporary] = None):
        self.opcode = opcode
        self.result = result
        self.operands: List[Value] = [ ]
