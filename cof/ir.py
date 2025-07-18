from enum import Enum
from typing import List, Optional, Union

mir_inst_id = 0
def new_id() -> int:
    global mir_inst_id
    mir_inst_id += 1
    return mir_inst_id

class OperandType(Enum):

    VAR = 1
    SSA_VAR = 2

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

    PHI = 77

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

class MIRInst:
    def __init__(self, **kwargs):
        self.id = new_id()

        self.addr = kwargs['addr']
        self.op = kwargs['op']
        self.operand1: Operand = kwargs['operand1']
        self.operand2: Operand = kwargs['operand2']
        self.result: Operand = kwargs['result']

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
    def _format_phi(self):
        return (
            f"{self._val(self.result)} := "
            f"{self._val(self.operand1)}("
            f"{self._val(self.operand2)})"
        )

    def _val(self, operand: Operand):
        return "" if operand is None else str(operand)


    def is_assignment(self) -> bool:
        return True if self.op in Assignment_Op else False
    def is_if(self) -> bool:
        return True if self.op == Op.IF else False
    def is_call(self) -> bool:
        return True if self.op == Op.CALL else False
    def is_phi(self) -> bool:
        return True if self.op == Op.PHI else False
    def get_assigned_var(self) -> Variable:
        assert self.result.type == OperandType.VAR
        return self.result.value
    def get_call_arg_list(self) -> List[Operand]:
        assert self.op == Op.CALL or self.op == Op.PHI
        assert self.operand2.type == OperandType.ARGS
        return self.operand2.value.args

    def ret_operand_list(self) -> List[Operand]:
        l: List[Operand] = []
        if self.is_assignment():
            l.append(self.result)
            l.append(self.operand1)
            if self.operand2:
                l.append(self.operand2)

        elif self.is_call():
            l = self.get_call_arg_list()

        elif self.is_if():
            l.append(self.operand1)

        elif self.is_phi():
            l = self.get_call_arg_list()

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