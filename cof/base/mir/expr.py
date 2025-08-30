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

    def __repr__(self):
        return f"{self.operand1} " + op_str(self.op) + f" {self.operand2}"

    def __eq__(self, other):
        return self.op == other.op \
            and self.operand1 == other.operand1 \
            and self.operand2 == other.operand2

    def __hash__(self):
        return hash((self.op, self.operand1, self.operand2))


def ret_expr_from_mir_inst(inst: MIRInst) -> Optional[Expression]:
    if inst.is_arithmetic():
        return Expression(
            op=inst.op,
            operand1=inst.operand1,
            operand2=inst.operand2,
            addr=inst.offset,
        )
    return None

def has_expr(inst: MIRInst, expr: Expression) -> bool:
    # ret_expr = ret_expr_from_mir_inst(inst)
    # return ret_expr == expr if ret_expr else False
    return ret_expr_from_mir_inst(inst) == expr

def convert_bin_expr_to_operand(inst: MIRInst, new_operand: Operand):

    if not inst.is_arithmetic():
        return

    inst.op = Op.ASSIGN
    inst.operand1 = new_operand
    inst.operand2 = None
