from typing import List, Dict, Tuple

from tabulate import tabulate

from cof.analysis.dataflow.framework import TransferCluster, B
from cof.base.bb import BasicBlock
from cof.base.mir.inst import MIRInstAddr
from cof.base.mir.variable import Variable
from cof.base.semilattice import Semilattice, T

type DefPoint = MIRInstAddr

def reaching_defs_on_state_change(block: BasicBlock, lattice, before: Tuple, after: Tuple):

    headers = [f"Block {block.id} "]
    row = ["Before"]
    row2 = ["After"]

    for idx, lat in enumerate(lattice.lattices):
        headers.append(str(lat.var))
        row.append(f"{{ {", ".join(map(str, before[idx]))} }}")
        row2.append(f"{{ {", ".join(map(str, after[idx]))} }}")

    table_data = [row, row2]
    print(tabulate(table_data, headers=headers, tablefmt="grid"), end="\n\n")



class ReachingDefsPowerSetSemilattice(Semilattice[set[DefPoint]]):

    def __init__(self, var: Variable, universal_set: set[DefPoint]):
        self.var = var
        self.universal_set = universal_set

    def top(self) -> T:
        return set()

    def bottom(self) -> T:
        return self.universal_set.copy()

    def partial_order(self, a: T, b: T) -> bool:
        return b.issubset(a)

    def meet(self, a: set[DefPoint], b: set[DefPoint]) -> set[DefPoint]:
        return a | b


class ReachingDefsProductSemilattice(Semilattice['Semilattice']):

    def __init__(self, defs_block: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]]):

        """
        As long as the dictionary content remains unmodified, the
        order returned by multiple calls to .values() will always
        be consistent with the insertion order.
        """
        self.var_to_lattice: Dict[Variable, ReachingDefsPowerSetSemilattice] = { }
        self.lattices: List[ReachingDefsPowerSetSemilattice] = []
        self.tuple_index: Dict[Variable, int] = { }
        self._initialize_lattices(defs_block)

    def _initialize_lattices(self, defs_block: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]]):
        for defs_list in defs_block.values():
            for defs in defs_list:
                var: Variable = defs[0]
                lattice = self.var_to_lattice.get(var)

                if not lattice:
                    lattice = ReachingDefsPowerSetSemilattice(var, set())
                    self.lattices.append(lattice)
                    self.tuple_index[var] = len(self.lattices) - 1
                    self.var_to_lattice[var] = lattice

                lattice.universal_set.add(defs[1])


    def meet(self, a: T, b: T) -> T:
        return tuple(
            lat.meet(a_i, b_i)
            for lat, a_i, b_i in zip(self.lattices, a, b)
        )

    def top(self) -> T:
        return tuple(lat.top() for lat in self.lattices)

    def bottom(self) -> T:
        return tuple(lat.bottom() for lat in self.lattices)

    def partial_order(self, a: T, b: T) -> bool:
        return all(
            lat.partial_order(a_i, b_i)
            for lat, a_i, b_i in zip(self.lattices, a, b)
        )


class ReachingDefsTransfer(TransferCluster):

    def __init__(self,
                 lattice: ReachingDefsProductSemilattice,
                 block_defs: Dict[BasicBlock, List[Tuple[Variable, DefPoint]]]):

        self.lattice = lattice
        self.block_defs = block_defs

        self.block_kill_gen = { }

        for block, defs in block_defs.items():
            killed_vars = {var for var, _ in defs}

            # compute gen set for each var.
            gen_sets = { }
            for var, def_stmt in defs:
                gen_sets.setdefault(var, set()).add(def_stmt)

            self.block_kill_gen[block] = (killed_vars, gen_sets)



    def apply(self, block: B, input_val: T) -> T:
        killed_vars, gen_sets = self.block_kill_gen.get(block, (set(), {}))
        out_state = list(input_val)

        for var in killed_vars:
            out_state[self.lattice.tuple_index[var]] = gen_sets.get(var, set())

        return tuple(out_state)
