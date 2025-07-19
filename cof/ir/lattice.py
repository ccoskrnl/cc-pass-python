from enum import Enum

from cof.ir.mir import OperandType


class LatticeState(Enum):
    # NAC, Not a Constant
    BOTTOM = 0,
    # Undecidable
    TOP = 1,
    # Constant
    CONSTANT = 2,

class ConstLattice:
    def __init__(self):
        self.state: LatticeState = LatticeState.TOP
        self.value = None
        self.type = None

    def set_constant(self, value) -> 'ConstLattice':
        self.state = LatticeState.CONSTANT
        self.value = value
        self.type = type(value)
        return self

    def set_bottom(self) -> 'ConstLattice':
        self.state = LatticeState.BOTTOM
        self.value = None
        self.type = None
        return self

    def set_top(self):
        """设置为TOP (未知状态)"""
        self.state = LatticeState.TOP
        self.value = None
        self.type = None
        return self

    def is_constant(self):
        return self.state == LatticeState.CONSTANT

    def is_bottom(self):
        return self.state == LatticeState.BOTTOM

    def is_top(self):
        return self.state == LatticeState.TOP


    def __iand__(self, other: 'ConstLattice') -> 'ConstLattice':
        """overload &= """
        if self.is_bottom() or other.is_bottom():
            self.state = LatticeState.BOTTOM
            return self

        if self.is_top():
            self.state = other.state
            self.type = other.type
            self.value = other.value

        if other.is_top():
            return self

        if self.value == other.value and self.type == other.type:
            return self
        else:
            self.state = LatticeState.BOTTOM

        return self

    def is_cond_true(self) -> bool:
        if self.state == LatticeState.CONSTANT:
            if self.type == OperandType.BOOL:
                return self.value
            elif self.type == OperandType.INT:
                return False if self.value == 0 else True
            return True
        else:
            return False

    def __repr__(self):
        if self.is_constant():
            return f"CONST({self.value})"
        if self.is_bottom():
            return "BOTTOM"
        return "TOP"

    def __eq__(self, other):
        if not isinstance(other, ConstLattice):
            return False
        return (self.state == other.state and
                self.value == other.value and
                self.type == other.type)
