from typing import Dict

from cof.analysis.dataflow.framework import TransferCluster, B
from cof.base.bb import BasicBlock
from cof.base.expr import Expression
from cof.base.semilattice import Semilattice, T


class AvailableExprSemilattice(Semilattice[set[Expression]]):

    def __init__(self, all_exprs: set[Expression]):
        self.all_exprs: set[Expression] = all_exprs

    def top(self) -> set[Expression]:
        return set()

    def bottom(self) -> set[Expression]:
        return self.all_exprs

    def meet(self, a: set[Expression], b: set[Expression]) -> set[Expression]:
        return a & b

    def partial_order(self, a: set[Expression], b: set[Expression]) -> bool:
        return b.issubset(a)

