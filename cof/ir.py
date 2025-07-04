from enum import Enum
from typing import List

class OperandType(Enum):

    ID = 1

    BOOL = 10
    FLOAT = 11
    INT = 12
    STR = 13

    OP = 20

    ADDR = 30

    UNKNOWN = 99


class Op(Enum):
    ADD = 1
    SUB = 2
    MUL = 3
    DIV = 4

    IF = 5
    GOTO = 6

    ASSIGN = 7

    LEQ = 8
    GEQ = 9
    LE = 10
    GE = 11
    EQ = 12
    NEQ = 13

    PHI = 95

    PRINT = 96
    ENTRY = 97
    EXIT = 98

    UNKNOWN = 99

OP_STR_MAP = {
    Op.ADD: "+",
    Op.SUB: "-",
    Op.MUL: "*",
    Op.DIV: "/",
    Op.IF: "if",
    Op.GOTO: "goto",
    Op.ASSIGN: ":=",
    Op.LEQ: "<=",
    Op.GEQ: ">=",
    Op.LE: "<",
    Op.GE: ">",
    Op.EQ: "=",
    Op.NEQ: "!=",
    Op.ENTRY: "entry",
    Op.EXIT: "exit",
    Op.PRINT: "print"
}

def op_str(op: Op) -> str:
    """Return string representation of operator"""
    return OP_STR_MAP.get(op, "UNKNOWN")

class Operand:
    def __init__(self, op_type: OperandType, value):
        self.type = op_type
        self.value = value

class Var:
    def __init__(self, varname: str):
        self.varname = varname

class IRInst:
    def __init__(self, **kwargs):
        self.op = kwargs['op']
        self.operand1 = kwargs['operand1']
        self.operand2 = kwargs['operand2']
        self.result = kwargs['result']

    def __repr__(self):
        formatter = {
            Op.IF: self._format_branch,
            Op.GOTO: self._format_jump,
            Op.ASSIGN: self._format_assign,
            Op.ENTRY: self._format_entry_exit,
            Op.EXIT: self._format_entry_exit,
            Op.PRINT: self._format_print,
        }.get(self.op, self._format_operator)

        return formatter()

    def _format_branch(self):
        return f"if {self._val(self.operand1)} goto addr_{self._val(self.result)}"
    def _format_jump(self):
        return f"goto addr_{self._val(self.result)}"
    def _format_assign(self):
        return f"{self._val(self.result)} := {self._val(self.operand1)}"
    def _format_entry_exit(self):
        return op_str(self.op)
    def _format_print(self):
        return f"print {self._val(self.operand1)}"
    def _format_operator(self):
        op_symbol = op_str(self.op)
        return (
            f"{self._val(self.result)} := "
            f"{self._val(self.operand1)} "
            f"{op_symbol} {self._val(self.operand2)}"
        )

    # noinspection PyMethodMayBeStatic
    def _val(self, item):
        return getattr(item, "value", None) if item is not None else "null"

class Insts:
    def __init__(self):
        self.ir_insts: List[IRInst] = []
        self.num: int = 0

    def add_an_inst(self, inst: IRInst):
        self.num += 1
        self.ir_insts.append(inst)
