from dataclasses import dataclass
from typing import Optional

from cof.base.mir import Op, MIRInstAddr, op_str



@dataclass
class Expression:
    """
    Representation of an expression in the program.
    """
    op: Op
    operands: tuple
    addr: MIRInstAddr
    hash_value: int

    def __repr__(self):
        return f"{self.operands[0]} " + op_str(self.op) + f" {self.operands[1]}"

    def __eq__(self, other):
        return self.hash_value == other.hash_value

    def __hash__(self):
        return self.hash_value


def ret_expr_from_mir_inst(inst) -> Optional[Expression]:
    if inst.is_arithmetic():
        return Expression(
            op=inst.op,
            operands=(inst.operand1, inst.operand2),
            addr=inst.addr,
            hash_value=hash((inst.op, inst.operand1.value, inst.operand2.value))
        )
    return None
