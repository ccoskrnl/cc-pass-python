from enum import Enum

from cof.ir.mir import OperandType


class LatticeState(Enum):
    # NAC, Not a Constant
    BOTTOM = 0,
    # Undecidable, but maybe a constant.
    TOP = 1,
    # Constant
    CONSTANT = 2,

class ConstLattice:
    def __init__(self):
        self.state: LatticeState = LatticeState.TOP
        self.value = None
        # self.type = None

    def set_constant(self, value) -> 'ConstLattice':
        self.state = LatticeState.CONSTANT
        self.value = value
        # self.type = t
        return self

    def set_bottom(self) -> 'ConstLattice':
        self.state = LatticeState.BOTTOM
        self.value = None
        # self.type = None
        return self

    def set_top(self):
        self.state = LatticeState.TOP
        self.value = None
        # self.type = None
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
            # self.type = other.type
            self.value = other.value
            return self

        if other.is_top():
            return self

        if self.is_constant() and self.is_constant():
            if self.value != other.value:
                self.set_bottom()

        return self

    def is_cond_true(self) -> bool:
        if self.state == LatticeState.CONSTANT:
            return self.value.is_true()
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
                self.value == other.value)
                # self.type == other.type)
