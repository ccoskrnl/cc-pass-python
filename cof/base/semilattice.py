from abc import ABC, abstractmethod
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
    def meet(self, other: T) -> T:
        pass

    @abstractmethod
    def is_less_or_equal(self, other: T) -> bool:
        pass

    @abstractmethod
    def __iand__(self, other) -> T:
        pass

    @abstractmethod
    def __eq__(self, other) -> bool:
        pass


class ConstLatState(Enum):
    # NAC, Not a Constant
    BOTTOM = 0,
    # Undecidable, but maybe a constant.
    TOP = 1,
    # Constant
    CONSTANT = 2,

class ConstLattice(Semilattice):

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


    def is_less_or_equal(self, other: 'ConstLattice') -> bool:
        if self.state == other.state or self.is_bottom:
            return True

        if self.state == ConstLatState.CONSTANT and other.state == ConstLatState.TOP:
            return True

        return False

    def meet(self, other: 'ConstLattice') -> 'ConstLattice':
        if self.is_bottom or other.is_bottom:
            return ConstLattice.bottom()

        if self.is_top:
            return other

        if other.is_top:
            return self

        if self.is_constant and self.is_constant:
            if self.value != other.value:
                return ConstLattice.bottom()

        return self

    def __iand__(self, other: 'ConstLattice') -> 'ConstLattice':
        """overload &= """
        result = self.meet(other)
        self.state = result.state
        self.value = result.value
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