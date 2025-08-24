from enum import Enum, auto
from typing import List, Optional, Union, Any, Callable


class OperandType(Enum):
    VOID = auto()

    VAR = auto()
    SSA_VAR = auto()

    BOOL = auto()
    FLOAT = auto()
    INT = auto()
    STR = auto()

    PTR = auto()

    ARGS = auto()

    UNKNOWN = auto()

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


class Variable:
    def __init__(self, varname: str):
        self.varname = varname
        self.temporary = False
    def __repr__(self):
        return self.varname
    def __hash__(self):
        return hash(self.varname)
    def __eq__(self, other):
        return self.varname == other.varname

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

    def __hash__(self):
        return hash((self.type, self.value))

    # ++++++++ repr ++++++++
    def __repr__(self):
        formatter = {
            OperandType.PTR: self._format_addr,
        }.get(self.type, self._format_const)
        return formatter()
    def _format_addr(self):
        return f"addr-{self.value}"
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
        return False if self.type == OperandType.BOOL and self.value == False else True



def mir_eval(op: Op, operand1: Operand, operand2: Operand) -> Operand:

    def normalize_operands(opnd1: Operand, opnd2: Operand) -> tuple:
        if opnd1.type == opnd2.type:
            return opnd1.value, opnd2.value, opnd1.type
        numeric_types = { OperandType.INT, OperandType.FLOAT }
        if opnd1.type in numeric_types and opnd2.type in numeric_types:
            # widening to float
            return float(opnd1.value), float(opnd2.value), OperandType.FLOAT

        raise TypeError("Incompatible operand types: "
                        f"{Operand_Type_Str_Map[opnd1.type]} and {Operand_Type_Str_Map[opnd2.type]}")

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
        Op.MOD: lambda a, b: a % b,
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
type MIRInstAddr = int

mir_inst_id = 0
def new_id() -> MIRInstId:
    global mir_inst_id
    mir_inst_id += 1
    return mir_inst_id

def _val(value) -> str:
    return str(value) if value else ""

class MIRInst:
    """

    if cond goto dest_addr
        inst.op = Op.IF
        inst.operand1 = Operand(cond)
        inst.result = Operand(dest_addr)

    retval := callee( arg1, arg2 )
        inst.op = Op.CALL_ASSIGN
        inst.operand1 = Operand(callee)
        inst.operand2 = Operand(Arg( arg1, arg 2))
        inst.result = Operand(retval)

    callee( arg1, arg 2)
        inst.op = Op.CALL
        inst.operand1 = Operand(callee)
        inst.operand2 = Operand(Arg( arg1, arg 2))

    """
    def __init__(self, **kwargs):
        self.global_id: MIRInstId = new_id()
        self.id: MIRInstId = 0
        self.addr: MIRInstAddr = kwargs['addr']
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
            Op.PHI: self._format_phi,
            Op.INIT: self._format_init
        }.get(self.op, self._format_operator)

        # return f"[ID:{self.id}]    {formatter()}"
        return formatter()

    def _format_init(self):
        return f"%init {_val(self.result)}"
    def _format_branch(self):
        return f"%if {_val(self.operand1)} %goto {_val(self.result)}"
    def _format_jump(self):
        return f"%goto {_val(self.result)}"
    def _format_assign(self):
        return f"{_val(self.result)} := {_val(self.operand1)}"
    def _format_entry_exit(self):
        return op_str(self.op)
    def _format_print(self):
        return f"%print {_val(self.operand1)}"
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
        return True if self.op in Evaluatable_Op else False
    def is_arithmetic(self) -> bool:
        return True if self.op in Arithmetic_Op else False
    def is_assignment(self) -> bool:
        return True if self.op in Assignment_Op else False
    def is_exp(self) -> bool:
        return True if self.op in Expression_Op else False
    def is_if(self) -> bool:
        return True if self.op == Op.IF else False
    def is_goto(self) -> bool:
        return True if self.op == Op.GOTO else False
    def is_call(self) -> bool:
        return True if self.op == Op.CALL or self.op == Op.CALL_ASSIGN else False
    def is_phi(self) -> bool:
        return True if self.op == Op.PHI else False
    def is_init(self) -> bool:
        return True if self.op == Op.INIT else False

    def ret_dest_variable(self) -> Optional[Operand]:
        """
        Retrieve the destination variable of the instruction.
        1. Return the assigned variable if it is an assignment instruction.
        2. Return the condition operand if it is a condition branch instruction.
        3. Return None if it is not one of the two type instructions above.
        """
        # assert self.result.type == OperandType.VAR
        if self.op in Assignment_Op:
            assert self.result
            return self.result
            # return self.result.value if self.result else None
        elif self.is_if():
            assert self.operand1
            return self.operand1
        return None

    def ret_assigned_var(self) -> Optional[Variable]:
        """
        Retrieve the assigned variable of the assignment instruction.
        """
        if self.is_assignment():
            assert self.result
            return self.result.value
        return None

    def ret_a_operand_list_for_evaluatable_exp_inst(self) -> List[Operand]:
        """
        Return an operand list for an evaluatable expression instruction.
        1. Add operands into the list if the instruction is a binary expression.
        2. Add condition operand into the list if the instruction is a condition branch.
        """
        if self.is_exp():
            return [self.operand1, self.operand2] if self.operand2 else [self.operand1]
        elif self.is_if():
            return [self.operand1]
        return []

    def ret_call_args_list(self) -> List[Operand]:
        """
        Return an arguments list for call instruction.
        You need to identify the instruction is call instruction before you call this method.
        """
        assert self.op == Op.CALL or self.op == Op.PHI or self.op == Op.CALL_ASSIGN
        assert self.operand2.type == OperandType.ARGS
        return self.operand2.value.args

    def ret_operand_list(self) -> List[Operand]:
        """
        Return an operand list for evaluatable instructions (include call instruction, but exclude goto )
        """
        l: List[Operand] = []

        if self.is_phi():
            l = self.ret_call_args_list()

        elif self.is_call():
            l = self.ret_call_args_list()

        elif self.is_exp():
            l.append(self.operand1)
            if self.operand2:
                l.append(self.operand2)

        elif self.is_if():
            l.append(self.operand1)

        return l

    def all_constant_operands(self):
        """
        check if all operands is constant, otherwise return false.
        """
        for operand in self.ret_a_operand_list_for_evaluatable_exp_inst():
            if operand.type not in Const_Operand_Type:
                return False
        return True


    def convert_if_to_goto(self):
        assert self.is_if()
        self.op = Op.GOTO
        self.operand1 = None
        self.operand2 = None



class MIRInsts:
    def __init__(self, insts:Optional[List[MIRInst]]):
        if insts:
            self.ir_insts: List[MIRInst] = insts
            self.num: int = len(insts)
        else:
            self.ir_insts: List[MIRInst] = []
            self.num: int = 0

        self.phi_insts_idx_end: int = 0

    # def inst_exist(self, inst: MIRInst) -> bool:
    #     for i in self.ret_insts():
    #         if i == inst:
    #             return True
    #     return False
    def inst_exist(self, predicate: Callable[[MIRInst], bool]) -> bool:
        for inst in self.ir_insts:
            if predicate(inst):
                return True
        return False

    def inst_exist_by_key(self, *, key: str, value: Any) -> bool:
        for inst in self.ir_insts:
            if getattr(inst, key) == value:
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

    def index_for_inst(self, inst: MIRInst) -> int:
        return self.ir_insts.index(inst)


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

    def highset_addr(self) -> int:
        return self.ir_insts[-1].addr

    def print(self):
        for inst in self.ir_insts:
            print(inst)