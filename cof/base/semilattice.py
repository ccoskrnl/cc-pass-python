from abc import ABC, abstractmethod
from copy import copy
from typing import Generic, Optional, Any
from enum import Enum
from typing import TypeVar

T = TypeVar('T')

class Semilattice(ABC, Generic[T]):
    """Semi-Lattice"""
    @abstractmethod
    def top(self) -> T:
        pass

    @abstractmethod
    def bottom(self) -> T:
        pass

    @abstractmethod
    def meet(self, a: T, b: T) -> T:
        pass

    def partial_order(self, a: T, b: T) -> bool:
        return self.meet(a, b) == a

class ConstLatState(Enum):
    # NAC, Not a Constant
    BOTTOM = 0,
    # Undecidable, but maybe a constant.
    TOP = 1,
    # Constant
    CONSTANT = 2,

class ConstLattice(Semilattice['ConstLattice']):

    def __init__(
            self,
            state: ConstLatState = ConstLatState.TOP,
            value: Optional[Any] = None
    ):
        self.state = state
        self.value = value

    @classmethod
    def top(cls) -> 'ConstLattice':
        return cls(ConstLatState.TOP)

    @classmethod
    def bottom(cls) -> 'ConstLattice':
        return cls(ConstLatState.BOTTOM)

    @classmethod
    def constant(cls, value: Any):
        return cls(ConstLatState.CONSTANT, value)


    @property
    def is_constant(self):
        return self.state == ConstLatState.CONSTANT

    @property
    def is_bottom(self):
        return self.state == ConstLatState.BOTTOM

    @property
    def is_top(self):
        return self.state == ConstLatState.TOP

    @property
    def is_cond_true(self) -> bool:
        if self.state == ConstLatState.CONSTANT:
            return self.value.is_true()
        else:
            return False

    def __copy__(self):
        """
        A shallow copy is already sufficient
        """
        return type(self)(self.state, self.value)

    def set_constant(self, value) -> 'ConstLattice':
        self.state = ConstLatState.CONSTANT
        self.value = value
        return self

    def set_bottom(self) -> 'ConstLattice':
        self.state = ConstLatState.BOTTOM
        self.value = None
        return self

    def set_top(self):
        self.state = ConstLatState.TOP
        self.value = None
        return self

    def partial_order(self, a: 'ConstLattice', b: 'ConstLattice') -> bool:
        if a.state == b.state or a.is_bottom:
            return True
        if a.state == ConstLatState.CONSTANT and b.state == ConstLatState.TOP:
            return True

        return False

    def meet(self, a: 'ConstLattice', b: 'ConstLattice') -> 'ConstLattice':
        if a.is_bottom or b.is_bottom:
            return ConstLattice.bottom()

        if a.is_top:
            return copy(b)

        if b.is_top:
            return copy(a)

        if a.is_constant and b.is_constant:
            if a.value != b.value:
                return ConstLattice.bottom()
        return copy(a)

    def copy(self, other: 'ConstLattice') -> None:
        self.state = other.state
        self.value = other.value

    def __xor__(self, other: 'ConstLattice') -> 'ConstLattice':
        """overload ^ """
        if self.is_bottom or other.is_bottom:
            return ConstLattice.bottom()

        if self.is_top:
            return copy(other)

        if other.is_top:
            return copy(self)

        if self.is_constant and self.is_constant:
            if self.value != other.value:
                return ConstLattice.bottom()

        return copy(self)

    def __ixor__(self, other: 'ConstLattice') -> 'ConstLattice':
        """overload ^= """
        if self.is_bottom or other.is_bottom:
            self.set_bottom()

        if self.is_top:
            self.copy(other)

        if self.is_constant and self.is_constant:
            if self.value != other.value:
                self.set_bottom()

        return self

    def __repr__(self):
        if self.is_constant:
            return f"CONST({self.value})"
        if self.is_bottom:
            return "BOTTOM"
        return "TOP"

    def __eq__(self, other):
        if not isinstance(other, ConstLattice):
            return False
        return (self.state == other.state and
                self.value == other.value)