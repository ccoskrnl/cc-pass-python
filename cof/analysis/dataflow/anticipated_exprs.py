"""
    Anticipated expressions analysis belongs to backward data-flow analysis problem.

    Assuming there is a block B_1, we need to figure out IN[B_1]. This is because
    when we compute the data-flow equation IN[B_1] = f_{B_1} ( OUT[B_1] ), we actually
    obtain the expression used in B_1. We put these expressions in IN[B_1], so that we
    can see these expressions(be referenced in B_1) at the entrance of B_1 and replace
    these expressions with temporary value which was computed before entering B_1.
"""
from typing import Dict, Set, List, Optional
from cof.analysis.dataflow.framework import TransferCluster
from cof.base.bb import BasicBlock
from cof.base.mir.expr import Expression, ret_expr_from_mir_inst
from cof.base.semilattice import Semilattice


class AnticipatedExprSemilattice(Semilattice[Set[Expression]]):

    def __init__(self, all_exprs: Set[Expression]):
        self.all_exprs: Set[Expression] = all_exprs

    def bottom(self) -> Set[Expression]:
        return self.all_exprs

    def meet(self, a: Set[Expression], b: Set[Expression]) -> Set[Expression]:
        return a & b

    def top(self) -> Set[Expression]:
        return set()



class AnticipatedTransfer(TransferCluster[BasicBlock, Set[Expression]]):

    def __init__(self, all_exprs: set[Expression], blocks: List[BasicBlock]):
        self.blocks = blocks
        self.all_exprs = all_exprs

        self.e_use_sets: Dict[BasicBlock, Set[Expression]] = self._comp_gen_sets()
        self.e_kill_sets: Dict[BasicBlock, Set[Expression]] = self._comp_kill_sets()

    def _comp_gen_sets(self) -> Dict[BasicBlock, Set[Expression]]:
        e_use_sets = {}

        for block in self.blocks:
            e_use = set()
            for inst in block.insts.ret_insts():
                expr: Optional[Expression] = ret_expr_from_mir_inst(inst)
                if expr is not None:
                    e_use.add(expr)

            e_use_sets[block] = e_use

        return e_use_sets

    def _comp_kill_sets(self) -> Dict[BasicBlock, Set[Expression]]:

        e_kill_sets = { }

        for block in self.blocks:
            kill = set()

            # Find all variables modified in this block.
            modified_vars = set()
            for inst in block.insts.ret_insts():
                assigned_var = inst.ret_assigned_var()
                if assigned_var is not None:
                    modified_vars.add(assigned_var)

            if modified_vars:
                for expr in self.all_exprs:
                    if ((expr.operands[0].value in modified_vars)
                            or (expr.operands[1].value in modified_vars)):
                        kill.add(expr)

            e_kill_sets[block] = kill

        return e_kill_sets



    def apply(self, block: BasicBlock, input_val: set[Expression]) -> set[Expression]:
        return self.e_use_sets.get(block, set()) | (input_val - self.e_kill_sets.get(block, set()))


def anticipated_exprs_on_state_change(block: BasicBlock, lattice, before: set[Expression], after: set[Expression]):
    print(f"Block {block.id}: {{ {", ".join(map(str, before))} }}  --->  {{ {", ".join(map(str, after))} }}")