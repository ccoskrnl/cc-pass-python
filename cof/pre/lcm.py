from typing import Dict

from cof.analysis.dataflow import AnticipatedSemilattice, AnticipatedTransfer, \
    DataFlowAnalysisFramework, anticipated_exprs_on_state_change
from cof.analysis.dataflow.available_expr import AvailableExprSemilattice
from cof.analysis.dataflow.framework import TransferFunction
from cof.base.bb import BasicBlock
from cof.base.cfg import ControlFlowGraph
from cof.base.expr import Expression
from cof.base.mir import MIRInsts


class LCMAvailableExprTransfer(TransferFunction[BasicBlock, set[Expression]]):

    def __init__(
            self,
            anticipated_exprs_in: Dict[BasicBlock, set[Expression]],
            kill_sets: Dict[BasicBlock, set[Expression]]
    ):
        self.anticipated_exprs_in: Dict[BasicBlock, set[Expression]] = anticipated_exprs_in
        self.kill_sets: Dict[BasicBlock, set[Expression]] = kill_sets


    def apply(self, block: BasicBlock, input_val: set[Expression]) -> set[Expression]:
        return (self.anticipated_exprs_in.get(block, set()) | input_val) - self.kill_sets.get(block, set())

def lazy_code_motion(cfg: ControlFlowGraph) -> MIRInsts:

    all_exprs = cfg.collect_exprs()

    """
    Step 1:
    Find all the expressions anticipated at each program point using a backward data-flow pass.
    """
    anticipated_exprs_lattice = AnticipatedSemilattice(all_exprs)
    anticipated_exprs_transfer_cluster = AnticipatedTransfer(anticipated_exprs_lattice, cfg.all_blocks())
    anticipated_exprs_analysis = DataFlowAnalysisFramework(
        cfg=cfg,
        lattice=anticipated_exprs_lattice,
        transfer=anticipated_exprs_transfer_cluster,
        direction='backward',
        init_value=anticipated_exprs_lattice.top(),
        safe_value=anticipated_exprs_lattice.bottom(),
        on_state_change=anticipated_exprs_on_state_change,
    )
    anticipated_exprs_analysis.analyze(strategy='worklist')

    """
    Step 2:
    The second step places the computation where the values of the expressions are first anticipated
    along some path. After we have placed copies of an expression where the expression is first anticipated,
    the expression would be available at program point p if it has been anticipated along all paths reaching p.
    Availability can be solved using a forward data-flow pass. If we wish to place the expressions at the
    earliest possible positions, **we can simply find those program points where the expressions are anticipated
    but are not available.**
    """

    available_exprs_lattice = AvailableExprSemilattice(all_exprs)
    available_exprs_transfer_cluster = LCMAvailableExprTransfer(
        anticipated_exprs_analysis.result,
        anticipated_exprs_transfer_cluster.kill_sets,
    )
    available_exprs_analysis = DataFlowAnalysisFramework(
        cfg=cfg,
        lattice=available_exprs_lattice,
        transfer=available_exprs_transfer_cluster,
        direction='forward',
        init_value=available_exprs_lattice.top(),
        safe_value=available_exprs_lattice.bottom(),
        on_state_change=anticipated_exprs_on_state_change
    )
    available_exprs_analysis.analyze(strategy='worklist')

    """
    Step 3:
    Executing an expression as soon as it is anticipated may produce a value long before it is used.
    An expression is postponable at a program point if the expression has been anticipated and has
    yet to be used along any path reaching the program point. 
    """

    """
    Step 4:
    A simple, final backward data-flow pass is used to eliminate assignments to temporary variables that
    are used only once in the program.
    """


    return MIRInsts(None)