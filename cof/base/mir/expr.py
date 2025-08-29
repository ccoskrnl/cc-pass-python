from dataclasses import dataclass
from typing import Optional

from cof.base.mir.inst import MIRInstAddr, MIRInst
from cof.base.mir.operand import Operand
from cof.base.mir.operator import op_str, Op


@dataclass
class Expression:
    """
    Representation of an expression in the program.
    """
    op: Op
    operand1: Operand
    operand2: Operand
    addr: MIRInstAddr
    hash_value: int

    def __repr__(self):
        return f"{self.operand1} " + op_str(self.op) + f" {self.operand2}"

    def __eq__(self, other):
        return self.hash_value == other.hash_value

    def __hash__(self):
        return self.hash_value


def ret_expr_from_mir_inst(inst: MIRInst) -> Optional[Expression]:
    if inst.is_arithmetic():
        return Expression(
            op=inst.op,
            operand1=inst.operand1,
            operand2=inst.operand2,
            addr=inst.addr,
            hash_value=hash((inst.op, inst.operand1.value, inst.operand2.value))
        )
    return None

def has_expr(inst: MIRInst, expr: Expression) -> bool:
    return ret_expr_from_mir_inst(inst) == expr

def convert_bin_expr_to_operand(inst: MIRInst, new_operand: Operand):

    if not inst.is_arithmetic():
        return

    inst.op = Op.ASSIGN
    inst.operand1 = new_operand
    inst.operand2 = None
