from enum import Enum
from typing import List

class OperandType(Enum):

    VAR = 1

    BOOL = 10
    FLOAT = 11
    INT = 12
    STR = 13

    ADDR = 30

    ARGS = 40

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

    CALL = 90

    PRINT = 96
    ENTRY = 97
    EXIT = 98

    UNKNOWN = 99

Assignment_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV,
    Op.ASSIGN,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ
}

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


class Variable:
    def __init__(self, varname: str):
        self.varname = varname
        self.temporary = False
    def __repr__(self):
        return self.varname

class Args:
    def __init__(self, args: List):
        self.args = args

    def __repr__(self):
        return ', '.join(map(str, self.args))

    # def __repr__(self):
    #     return f"{self.__class__.__name__}({', '.join(map(repr, self.args))})"


class Operand:
    def __init__(self, op_type: OperandType, value):
        self.type = op_type
        self.value = value

    def __repr__(self):
        formatter = {
            OperandType.ADDR: self._format_addr,
        }.get(self.type, self._format_const)
        return formatter()

    def _format_addr(self):
        return f"addr_{self.value}"

    def _format_const(self):
        return str(self.value)

class IRInst:
    """
    a = b + c: (op=ADD, operand1=b, operand2=c, result=a)
    m = max(b, c): (op=CALL,
                    operand1=max,
                    operand2=Args([Operand(OperandType.VAR, b), Operand(OperandType.VAR, c)]),
                    result=m)

    """
    def __init__(self, **kwargs):
        self.op = kwargs['op']
        self.operand1: Operand = kwargs['operand1']
        self.operand2: Operand = kwargs['operand2']
        self.result: Operand = kwargs['result']

    def __repr__(self):
        formatter = {
            Op.IF: self._format_branch,
            Op.GOTO: self._format_jump,
            Op.ASSIGN: self._format_assign,
            Op.ENTRY: self._format_entry_exit,
            Op.EXIT: self._format_entry_exit,
            Op.PRINT: self._format_print,
            Op.CALL: self._format_call
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
    def _format_call(self):
        if self.result:
            return (
                f"{self._val(self.result)} := "
                f"{self._val(self.operand1)}("
                f"{self._val(self.operand2)})"
            )
        else:
            return (
                f"{self._val(self.operand1)}("
                f"{self._val(self.operand2)})"
            )

    def _val(self, operand: Operand):
        return "" if operand is None else str(operand)

def is_assignment_inst(inst: IRInst) -> bool:
    return True if inst.op in Assignment_Op else False

def get_assigned_var(inst: IRInst) -> Variable:
    assert inst.result.type == OperandType.VAR
    return inst.result.value

def create_phi_function(varname: str, num_pred_s: int):
    # create argument list: [undef] * num_predecease
    args: List[Operand] = []
    for i in range(0, num_pred_s):
        args.append(Operand(OperandType.VAR, Variable(varname + '?')))

    return IRInst(
        op=Op.CALL,
        operand1=Operand(OperandType.VAR, Variable("φ")),
        operand2=Operand(OperandType.ARGS, Args(args)),
        result = Operand(OperandType.VAR, Variable(varname)),
    )

class Insts:
    def __init__(self):
        self.ir_insts: List[IRInst] = []
        self.num: int = 0

    def add_an_inst(self, inst: IRInst):
        self.num += 1
        self.ir_insts.append(inst)
