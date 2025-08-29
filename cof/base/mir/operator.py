from enum import Enum, auto


class Op(Enum):
    MOD = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()

    IF = auto()
    GOTO = auto()

    ASSIGN = auto()

    LEQ = auto()
    GEQ = auto()
    LE = auto()
    GE = auto()
    EQ = auto()
    NEQ = auto()

    PHI = auto()

    CALL = auto()
    CALL_ASSIGN = auto()

    PRINT = auto()
    INIT = auto()
    ENTRY = auto()
    EXIT = auto()

    UNKNOWN = auto()

Arithmetic_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ,
}
# bool op
Bool_Op = {
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ
}
# All evaluatable expressions.
Evaluatable_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD,
    Op.ASSIGN,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ,
    Op.IF
}
Expression_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD,
    Op.ASSIGN,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ,
}

# All operators with assignment operation
Assignment_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.MOD,
    Op.ASSIGN,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ,
    Op.PHI, Op.CALL_ASSIGN,
    Op.INIT,
}
OP_STR_MAP = {
    Op.ADD: "+",
    Op.SUB: "-",
    Op.MUL: "*",
    Op.DIV: "/",
    Op.MOD: "%",
    Op.IF: "%if",
    Op.GOTO: "%goto",
    Op.ASSIGN: ":=",
    Op.LEQ: "<=",
    Op.GEQ: ">=",
    Op.LE: "<",
    Op.GE: ">",
    Op.EQ: "=",
    Op.NEQ: "!=",
    Op.PHI: "φ",
    Op.ENTRY: "%entry",
    Op.EXIT: "%exit",
    Op.PRINT: "%print",
    Op.INIT: "%init",
}
def op_str(op: Op) -> str:
    """Return string representation of operator"""
    return OP_STR_MAP.get(op, "UNKNOWN")
