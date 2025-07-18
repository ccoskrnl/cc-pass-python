from enum import Enum

class LatticeState(Enum):
    BOTTOM = 0,
    TOP = 1,
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

    def meet(self, other):
        """
        格上的meet操作（下确界）
        合并两个格值，返回新格值
        """
        # 如果任一为BOTTOM，结果为BOTTOM
        if self.is_bottom() or other.is_bottom():
            return ConstLattice().set_bottom()

        # 如果自身为TOP，返回other
        if self.is_top():
            return other.copy()

        # 如果other为TOP，返回自身
        if other.is_top():
            return self.copy()

        # 两者都是常数
        if self.value == other.value and self.type == other.type:
            return self.copy()  # 相同值

        # 值不同，冲突
        return ConstLattice().set_bottom()

    def copy(self):
        """创建副本"""
        new_lattice = ConstLattice()
        new_lattice.state = self.state
        new_lattice.value = self.value
        new_lattice.type = self.type
        return new_lattice

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
