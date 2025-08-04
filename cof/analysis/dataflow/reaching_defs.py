from collections import defaultdict
from copy import deepcopy
from typing import Set, List, Dict

from cof.analysis.dataflow.framework import TransferFunction
from cof.base.bb import BasicBlock
from cof.base.mir import MIRInstAddr, Variable
from cof.base.semilattice import Semilattice


class Definition:
    def __init__(self, var: Variable, location: MIRInstAddr):
        self.var = var
        self.location = location

    def __hash__(self):
        return hash((self.var, self.location))

    def __eq__(self, other):
        return isinstance(other, Definition) and \
            self.var == other.var and \
            self.location == other.location

    def __str__(self):
        return f"({self.var}, addr={self.location})"

class ReachingDefLattice(Semilattice[set[Definition]]):
    """
    A Semilattice L = (V, meet='Union', partial_order='superset')
    """

    def __init__(self, all_definitions: set[Definition]):
        self.all_defs = all_definitions

    def top(self) -> set[Definition]:
        return set()

    def bottom(self) -> set[Definition]:
        return self.all_defs

    def meet(self, values: List[Set[Definition]]) -> Set[Definition]:
        if not values:
            return set()
        copied_result = deepcopy(values[0])
        for val in values[1:]:
            copied_result |= val
        return copied_result

    def is_less_or_equal(self, a: set[Definition], b: set[Definition]) -> bool:
        """
        The partial order is superset.
        We say a_value is less or equal b_value when a_value is a superset of the b_value
        """
        return b.issubset(a)

class ReachingDefTransfer(TransferFunction[set[Definition], BasicBlock]):
    def __init__(self, block_defs: Dict[BasicBlock, set[Definition]]):

        self.block_gen: Dict[BasicBlock, set[Definition]] = block_defs

        var_to_defs = defaultdict(set)
        for def_set in block_defs.values():
            for d in def_set:
                var_to_defs[d.var].add(d)

        self.block_kill: Dict[BasicBlock, set[Definition]] = defaultdict(set)
        for block, defs in block_defs.items():
            killed_vars = {d.var for d in defs}
            for var in killed_vars:
                self.block_kill[block] |= var_to_defs[var] - defs

    def apply(self, block: BasicBlock, input_val: set[Definition]) -> set[Definition]:
        return (input_val - self.block_kill.get(block, set())) | \
                self.block_gen.get(block, set())

def reaching_defs_on_state_change(block: BasicBlock, before: set[Definition], after: set[Definition]):
    print(f"Block {block.id}: {{ {", ".join(map(str, before))} }}  --->  {{ {", ".join(map(str, after))} }}")