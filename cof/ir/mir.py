from enum import Enum
from typing import List, Optional, Union, Any, Callable


class OperandType(Enum):
    VOID = 0

    VAR = 1
    SSA_VAR = 2

    BOOL = 10
    FLOAT = 11
    INT = 12
    STR = 13

    PTR = 30

    ARGS = 40

    UNKNOWN = 99

Operand_Type_Str_Map = {
    OperandType.VOID : "void",
    OperandType.VAR: "var",
    OperandType.SSA_VAR: "ssa var",
    OperandType.INT: "int",
    OperandType.FLOAT: "float",
    OperandType.BOOL: "bool",
    OperandType.STR: "str",
    OperandType.PTR: "ptr",
    OperandType.ARGS: "args",
    OperandType.UNKNOWN: "unknown",
}

Const_Operand_Type = {
    OperandType.BOOL,
    OperandType.FLOAT,
    OperandType.INT,
    OperandType.STR
}


class Type:
    def __init__(self, name: OperandType):
        self.name = name
    def __repr__(self):
        return self.name
    def __eq__(self, other):
        self.name = other.name

    def is_void(self):
        return True if self.name == OperandType.VOID else False
    def is_const(self):
        return True if self.name in Const_Operand_Type else False
    def is_ssa_var(self) -> bool:
        return True if self.name == OperandType.SSA_VAR else False
    def is_var(self) -> bool:
        return True if self.name == OperandType.VAR else False
    def is_ptr(self) -> bool:
        return True if self.name == OperandType.PTR else False

VOID = Type(OperandType.VOID)

INT = Type(OperandType.INT)
FLOAT = Type(OperandType.FLOAT)
BOOL = Type(OperandType.BOOL)
STR = Type(OperandType.STR)

SSA_VAR = Type(OperandType.SSA_VAR)
VAR = Type(OperandType.VAR)

PTR = Type(OperandType.PTR)


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

    PHI = 77

    CALL = 90
    CALL_ASSIGN = 91

    PRINT = 96
    ENTRY = 97
    EXIT = 98

    UNKNOWN = 99
# bool op
Bool_Op = {
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ
}
# All evaluatable expressions.
Exp_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV,
    Op.ASSIGN,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ,
    Op.IF
}
# All operators with assignment operation
Assignment_Op = {
    Op.ADD, Op.SUB, Op.MUL, Op.DIV,
    Op.ASSIGN,
    Op.LEQ, Op.GEQ, Op.LE, Op.GE, Op.EQ, Op.NEQ,
    Op.PHI, Op.CALL_ASSIGN
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
    Op.PHI: "φ",
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

    # ++++++++ init ++++++++
    def __init__(self, op_type: OperandType, value):
        self.type = op_type
        self.value = value

    def __eq__(self, other):
        return True if self.type == other.type \
                       and self.value == other.value else False

    # ++++++++ repr ++++++++
    def __repr__(self):
        formatter = {
            OperandType.PTR: self._format_addr,
        }.get(self.type, self._format_const)
        return formatter()
    def _format_addr(self):
        return f"addr_{self.value}"
    def _format_const(self):
        return str(self.value)
    def _val(self, operand: 'Operand'):
        assert isinstance(self.type, OperandType)
        return "" if operand is None else str(operand)

    # ++++++++ type ++++++++
    def is_const(self) -> bool:
        return True if self.type else False
    def is_ssa_var(self) -> bool:
        return True if self.type == OperandType.SSA_VAR else False
    def is_var(self) -> bool:
        return True if self.type == OperandType.VAR else False
    def is_ptr(self) -> bool:
        return True if self.type == OperandType.PTR else False
    def is_void(self) -> bool:
        return True if self.type == OperandType.VOID else False

    # ++++++++ value ++++++++
    def is_true(self) -> bool:
        return True if self.type == OperandType.BOOL and self.value == True else False



def mir_eval(op: Op, operand1: Operand, operand2: Operand) -> Operand:

    def normalize_operands(op1: Operand, op2: Operand) -> tuple:
        if op1.type == op2.type:
            return op1.value, op2.value, op1.type
        numeric_types = { OperandType.INT, OperandType.FLOAT }
        if op1.type in numeric_types and op2.type in numeric_types:
            # widening to float
            return float(op1.value), float(op2.value), OperandType.FLOAT

        raise TypeError("Incompatible operand types: "
                        f"{Operand_Type_Str_Map[op1.type]} and {Operand_Type_Str_Map[op2.type]}")

    def safe_divide(a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Division by zero")
        return a / b

    op1, op2, result_type = normalize_operands(operand1, operand2)

    op_handlers = {
        Op.ADD: lambda a, b: a + b,
        Op.SUB: lambda a, b: a - b,
        Op.MUL: lambda a, b: a * b,
        Op.DIV: safe_divide,
        Op.LE: lambda a, b: a < b,
        Op.GE: lambda a, b: a > b,
        Op.LEQ: lambda a, b: a <= b,
        Op.GEQ: lambda a, b: a >= b,
        Op.EQ: lambda a, b: a == b,
        Op.NEQ: lambda a, b: a != b,
    }

    if op not in op_handlers:
        return Operand(OperandType.UNKNOWN, None)

    handler = op_handlers[op]
    result_value = handler(op1, op2)

    final_type = OperandType.BOOL if op in Bool_Op else result_type

    return Operand(final_type, result_value)




# ++++++++++++++++++++++++ MIR ++++++++++++++++++++

type MIRInstId = int

mir_inst_id = 0
def new_id() -> MIRInstId:
    global mir_inst_id
    mir_inst_id += 1
    return mir_inst_id

def _val(value) -> str:
    return str(value) if value else ""

class MIRInst:
    def __init__(self, **kwargs):
        self.id: MIRInstId = new_id()

        self.addr = kwargs['addr']
        self.op = kwargs['op']
        self.operand1: Operand = kwargs['operand1']
        self.operand2: Operand = kwargs['operand2']
        self.result: Operand = kwargs['result']
    def __hash__(self):
        return hash(self.id)
    def __eq__(self, other):
        if not isinstance(other, MIRInst):
            return False
        return self.id == other.id
    def __repr__(self):
        formatter = {
            Op.IF: self._format_branch,
            Op.GOTO: self._format_jump,
            Op.ASSIGN: self._format_assign,
            Op.ENTRY: self._format_entry_exit,
            Op.EXIT: self._format_entry_exit,
            Op.PRINT: self._format_print,
            Op.CALL: self._format_call,
            Op.PHI: self._format_phi
        }.get(self.op, self._format_operator)

        return f"[ID:{self.id}]    {formatter()}"
        # return formatter()

    def _format_branch(self):
        return f"if {_val(self.operand1)} goto addr_{_val(self.result)}"
    def _format_jump(self):
        return f"goto addr_{_val(self.result)}"
    def _format_assign(self):
        return f"{_val(self.result)} := {_val(self.operand1)}"
    def _format_entry_exit(self):
        return op_str(self.op)
    def _format_print(self):
        return f"print {_val(self.operand1)}"
    def _format_operator(self):
        op_symbol = op_str(self.op)
        return (
            f"{_val(self.result)} := "
            f"{_val(self.operand1)} "
            f"{op_symbol} {_val(self.operand2)}"
        )
    def _format_call(self):
        if self.result:
            return (
                f"{_val(self.result)} := "
                f"{_val(self.operand1)}("
                f"{_val(self.operand2)})"
            )
        else:
            return (
                f"{_val(self.operand1)}("
                f"{_val(self.operand2)})"
            )
    def _format_phi(self):
        return (
            f"{_val(self.result)} := "
            f"{_val(self.operand1)}("
            f"{_val(self.operand2)})"
        )

    def is_evaluatable(self) -> bool:
        return True if self.op in Exp_Op else False
    def is_assignment(self) -> bool:
        return True if self.op in Assignment_Op else False
    def is_if(self) -> bool:
        return True if self.op == Op.IF else False
    def is_call(self) -> bool:
        return True if self.op == Op.CALL or self.op == Op.CALL_ASSIGN else False
    def is_phi(self) -> bool:
        return True if self.op == Op.PHI else False

    def get_assigned_var(self) -> Optional[Variable]:
        # assert self.result.type == OperandType.VAR
        return self.result.value if self.result else None
    def get_call_arg_list(self) -> List[Operand]:
        assert self.op == Op.CALL or self.op == Op.PHI
        assert self.operand2.type == OperandType.ARGS
        return self.operand2.value.args
    def ret_operand_list_of_exp(self) -> List[Operand]:
        l: List[Operand] = []
        if self.is_assignment():
            l.append(self.operand1)
            if self.operand2:
                l.append(self.operand2)

        elif self.is_if():
            l.append(self.operand1)

        return l
    def ret_operand_list(self) -> List[Operand]:
        l: List[Operand] = []

        if self.is_phi():
            l = self.get_call_arg_list()

        elif self.is_call():
            l = self.get_call_arg_list()

        elif self.is_assignment():
            l.append(self.operand1)
            if self.operand2:
                l.append(self.operand2)

        elif self.is_if():
            l.append(self.operand1)

        return l



class MIRInsts:
    def __init__(self, insts:Optional[List[MIRInst]]):
        if insts:
            self.ir_insts: List[MIRInst] = insts
            self.num: int = len(insts)
        else:
            self.ir_insts: List[MIRInst] = []
            self.num: int = 0

        self.phi_insts_idx_end: int = 0

    def inst_exist(self, inst: MIRInst) -> bool:
        for i in self.ret_insts():
            if i == inst:
                return True
        return False
    def inst_exist_by_id(self, inst_id: int) -> bool:
        for i in self.ret_insts():
            if i.id == inst_id:
                return True
        return False
    def inst_exist_by_addr(self, addr: int) -> bool:
        for inst in self.ret_insts():
            if inst.addr == addr:
                return True
        return False

    def add_phi_inst(self, phi_inst: MIRInst) -> None:
        self.ir_insts.insert(0, phi_inst)
        self.phi_insts_idx_end += 1
    def insert_insts(self, index: Optional[int], insts: Union[MIRInst, List[MIRInst]]) -> None:

        if not index or index >= self.num:
            index = self.num

        if isinstance(insts, MIRInst):
            self.ir_insts.insert(index, insts)
            self.num += 1
        elif isinstance(insts, List) and all(isinstance(item, MIRInst) for item in insts):
            self.ir_insts[index:index] = insts
            self.num += len(insts)

    def find_inst_by_key(self, *, key: str, value: Any) -> Optional[MIRInst]:
        for inst in self.ir_insts:
            if getattr(inst, key) == value:
                return inst
        return None
    # find_inst(lambda i: i.addr == 0x1000)
    def find_inst(self, predicate: Callable[[MIRInst], bool]) -> Optional[MIRInst]:
        for inst in self.ir_insts:
            if predicate(inst):
                return inst
        return None

    def ret_inst_by_idx(self, index: int) -> MIRInst:
        return self.ir_insts[index]
    def ret_insts_by_pos(self, start_pos: int, end_pos: int) -> List[MIRInst]:
        return self.ir_insts[start_pos:end_pos]
    def ret_insts(self) -> List[MIRInst]:
        return self.ir_insts
    def ret_phi_insts(self) -> List[MIRInst]:
        return self.ir_insts[: self.phi_insts_idx_end]
    def ret_ordinary_insts(self) -> List[MIRInst]:
        return self.ir_insts[self.phi_insts_idx_end:]