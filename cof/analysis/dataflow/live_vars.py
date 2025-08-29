from typing import Dict

from cof.analysis.dataflow.framework import TransferCluster
from cof.base.bb import BasicBlock
from cof.base.mir.variable import Variable
from cof.base.semilattice import Semilattice, T


class LiveVarsLattice(Semilattice[set[Variable]]):
    def __init__(self, all_vars: set[Variable]):
        self.all_vars: set[Variable] = all_vars

    def top(self) -> set[Variable]:
        return set()

    def bottom(self) -> set[Variable]:
        return self.all_vars

    def meet(self, a: T, b: T) -> T:
        return a | b

    def partial_order(self, a: set[Variable], b: set[Variable]) -> bool:
        return b.issubset(a)

class LiveVarsTransfer(TransferCluster):
    def __init__(self, use_dict: Dict[BasicBlock, set[Variable]], def_dict: Dict[BasicBlock, set[Variable]]):
        self.use_dict: Dict[BasicBlock, set[Variable]] = use_dict
        self.def_dict: Dict[BasicBlock, set[Variable]] = def_dict

    def apply(self, block: BasicBlock, input_val: set[Variable]) -> set[Variable]:
        return self.use_dict.get(block, set()) | (input_val - self.def_dict.get(block, set()))


def live_vars_on_state_change(block: BasicBlock, lattice, before: set[Variable], after: set[Variable]):
    print(f"Block {block.id}: {{ {", ".join(map(str, before))} }}  --->  {{ {", ".join(map(str, after))} }}")
