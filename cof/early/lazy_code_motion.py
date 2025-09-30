from copy import deepcopy
from typing import Dict, Optional, List, Callable

from cof.analysis.dataflow import DataFlowAnalysisFramework
from cof.analysis.dataflow.framework import TransferCluster
from cof.base.bb import BasicBlock, BasicBlockId
from cof.base.cfg import ControlFlowGraph
from cof.base.mir.expr import Expression, has_expr, convert_bin_expr_to_operand, ret_expr_from_mir_inst
from cof.base.mir.inst import MIRInst
from cof.base.mir.operand import OperandType, Operand
from cof.base.mir.variable import Variable, LCM_TMP_VAR_PREFIX
from cof.base.semilattice import Semilattice


class LCMAnticipatedExprSemilattice(Semilattice[set[Expression]]):

    def __init__(self, all_exprs: set[Expression]):
        self.universal_set: set[Expression] = all_exprs

    def bottom(self) -> set[Expression]:
        return set()

    def meet(self, a: set[Expression], b: set[Expression]) -> set[Expression]:
        return a & b

    def top(self) -> set[Expression]:
        return self.universal_set

class LCMAvailableExprSemilattice(Semilattice[set[Expression]]):
    def __init__(self, all_exprs: set[Expression]):
        self.universal_set: set[Expression] = all_exprs

    def bottom(self) -> set[Expression]:
        return set()

    def meet(self, a: set[Expression], b: set[Expression]) -> set[Expression]:
        return a & b

    def top(self) -> set[Expression]:
        return self.universal_set


class LCMPostponableExprSemilattice(Semilattice[set[Expression]]):

    def __init__(self, all_exprs: set[Expression]):
        self.universal_set: set[Expression] = all_exprs

    def top(self) -> set[Expression]:
        return self.universal_set

    def bottom(self) -> set[Expression]:
        return set()

    def meet(self, a: set[Expression], b: set[Expression]) -> set[Expression]:
        return a & b

class LCMUsedExprSemilattice(Semilattice[set[Expression]]):

    def __init__(self, all_exprs: set[Expression]):
        self.all_exprs: set[Expression] = all_exprs

    def top(self) -> set[Expression]:
        return set()

    def bottom(self) -> set[Expression]:
        return self.all_exprs

    def meet(self, a: set[Expression], b: set[Expression]) -> set[Expression]:
        return a & b


class LCMAnticipatedExprTransferCluster(TransferCluster[BasicBlock, set[Expression]]):

    def __init__(
            self,
            e_use_sets: Dict[BasicBlock, set[Expression]],
            e_kill_sets: Dict[BasicBlock, set[Expression]],
    ):
        self.e_use_sets = e_use_sets
        self.e_kill_sets = e_kill_sets

    def apply(self, block: BasicBlock, input_val: set[Expression]) -> set[Expression]:
        return self.e_use_sets.get(block, set()) | (input_val - self.e_kill_sets.get(block, set()))

class LCMAvailableExprTransferCluster(TransferCluster[BasicBlock, set[Expression]]):

    def __init__(
            self,
            anticipated_exprs_in: Dict[BasicBlock, set[Expression]],
            kill_sets: Dict[BasicBlock, set[Expression]]
    ):
        self.anticipated_exprs_in: Dict[BasicBlock, set[Expression]] = anticipated_exprs_in
        self.kill_sets: Dict[BasicBlock, set[Expression]] = kill_sets


    def apply(self, block: BasicBlock, input_val: set[Expression]) -> set[Expression]:
        return (self.anticipated_exprs_in.get(block, set()) | input_val) - self.kill_sets.get(block, set())

class LCMPostponableExprTransferCluster(TransferCluster[BasicBlock, set[Expression]]):
    def __init__(
            self,
            earliest_set: Dict[BasicBlock, set[Expression]],
            e_use_set: Dict[BasicBlock, set[Expression]],
    ):
        self.earliest_set = earliest_set
        self.e_use_set = e_use_set

    def apply(self, block: BasicBlock, input_val: set[Expression]) -> set[Expression]:
        return (self.earliest_set.get(block, set()) | input_val) - self.e_use_set.get(block, set())

class LCMUsedExprTransferCluster(TransferCluster[BasicBlock, set[Expression]]):
    def __init__(
            self,
            e_use_set: Dict[BasicBlock, set[Expression]],
            latest_set: Dict[BasicBlock, set[Expression]],
    ):
        self.e_use_set = e_use_set
        self.latest_set = latest_set

    def apply(self, block: BasicBlock, input_val: set[Expression]) -> set[Expression]:
        return (self.e_use_set.get(block, set()) | input_val) - self.latest_set.get(block, set())


def expr_on_state_change(block: BasicBlock, lattice, before: set[Expression], after: set[Expression]):
    print(f"Block {block.id}: {{ {", ".join(map(str, before))} }}  --->  {{ {", ".join(map(str, after))} }}")

def _comp_e_use_sets(blocks: List[BasicBlock]) -> Dict[BasicBlock, set[Expression]]:

    e_use_sets = { }

    for block in blocks:
        e_use = set()
        for inst in block.insts.ret_insts():
            expr: Optional[Expression] = ret_expr_from_mir_inst(inst)
            if expr is not None:
                e_use.add(expr)
        e_use_sets[block] = e_use

    return e_use_sets

def _comp_e_kill_sets(
        blocks: List[BasicBlock],
        all_exprs: set[Expression]
) -> Dict[BasicBlock, set[Expression]]:

    e_kill_sets = { }

    for block in blocks:
        kill = set()

        # Find all variables modified in this block.
        modified_vars = set()
        for inst in block.insts.ret_insts():
            assigned_var = inst.ret_def_var()
            if assigned_var is not None:
                modified_vars.add(assigned_var)

        if modified_vars:
            for expr in all_exprs:
                if ((expr.operand1.value in modified_vars)
                        or (expr.operand2.value in modified_vars)):
                    kill.add(expr)

        e_kill_sets[block] = kill

    return e_kill_sets

def _comp_latest_sets(
        blocks: List[BasicBlock],
        succ: Callable[[BasicBlockId], List[BasicBlock]],
        all_exprs: set[Expression],
        earliest_set: Dict[BasicBlock, set[Expression]],
        postponable_in_set: Dict[BasicBlock, set[Expression]],
        e_use_set: Dict[BasicBlock, set[Expression]],
) -> Dict[BasicBlock, set[Expression]]:

    latest = { }
    for block in blocks:

        # Compute \neg \big(\bigcap_{S, succ[B]}(earliest[S] \cup postponable[S].in) \big)

        succ_s: List[BasicBlock] = succ(block.id)
        ep_list: List = [ None ] * len(succ_s)

        # compute (earliest[S] \cup postponable[S].in)
        for i, s in enumerate(succ_s):
            ep_list[i] = earliest_set[s] | postponable_in_set[s]

        # compute the intersection
        r = set()
        if ep_list:
            r = ep_list[0]
            for ep in ep_list[1:]:
                r &= ep

        # compute \neg
        comp_r = all_exprs - r

        # Compute \big( e\_use_{B} \cup \neg \big(\bigcap_{S, succ[B]}(earliest[S] \cup postponable[S].in) \big) \big)
        second = e_use_set[block] | comp_r

        # Compute (earliest[B] \cup postponable[B].in)
        first = earliest_set[block] | postponable_in_set[block]

        # compute the interaction of first and second.
        latest[block] = first & second

    return latest

def _comp_earliest_sets(
        blocks: List[BasicBlock],
        all_exprs: set[Expression],
        antic_in_set: Dict[BasicBlock, set[Expression]],
        avail_in_set: Dict[BasicBlock, set[Expression]],
) -> Dict[BasicBlock, set[Expression]]:
    earliest = { }

    for block in blocks:
        antic_in = antic_in_set.get(block, set())
        avail_in = avail_in_set.get(block, set())
        comp_avail = all_exprs - avail_in
        earliest[block] = antic_in & comp_avail

    return earliest




def lazy_code_motion_optimize(cfg: ControlFlowGraph):

    blocks: List[BasicBlock] = cfg.all_blocks()
    all_exprs = cfg.collect_exprs()


    # $e\_use_{B}$ is the set of expressions computed in $B$ and $e\_kill_{B}$ is
    # the set of expressions killed, that is, the set of expressions any of whose
    # operands are defined in $B$.
    e_use_sets: Dict[BasicBlock, set[Expression]] = _comp_e_use_sets(blocks)
    e_kill_sets: Dict[BasicBlock, set[Expression]] = _comp_e_kill_sets(blocks, all_exprs)



    """
    Step 1:
    Find all the expressions anticipated at each program point using a backward data-flow pass.
    """
    anticipated_exprs_lattice = LCMAnticipatedExprSemilattice(all_exprs)
    anticipated_exprs_transfer_cluster = LCMAnticipatedExprTransferCluster(e_use_sets, e_kill_sets)
    anticipated_exprs_analysis = DataFlowAnalysisFramework(
        cfg=cfg,
        lattice=anticipated_exprs_lattice,
        transfer=anticipated_exprs_transfer_cluster,
        direction='backward',
        init_value=anticipated_exprs_lattice.bottom(),
        safe_value=anticipated_exprs_lattice.top(),
        # on_state_change=expr_on_state_change,
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

    available_exprs_lattice = LCMAvailableExprSemilattice(all_exprs)
    available_exprs_transfer_cluster = LCMAvailableExprTransferCluster(
        anticipated_exprs_analysis.in_states,
        anticipated_exprs_transfer_cluster.e_kill_sets,
    )
    available_exprs_analysis = DataFlowAnalysisFramework(
        cfg=cfg,
        lattice=available_exprs_lattice,
        transfer=available_exprs_transfer_cluster,
        direction='forward',
        init_value=available_exprs_lattice.bottom(),
        safe_value=available_exprs_lattice.top(),
        # on_state_change=expr_on_state_change
    )
    available_exprs_analysis.analyze(strategy='worklist')

    """
    Step 3:
    The third step postpones the computation of expressions as much as possible while preserving the
    original program semantics and minimizing redundancy.
    
    Executing an expression as soon as it is anticipated may produce a value long before it is used.
    An expression is postponable at a program point if the expression has been anticipated and has
    yet to be used along any path reaching the program point. 
    
    Formally, an expression $x + y$ is postponable at a program point $p$ if an early placement of
    $x + y$ is encountered along every path from the entry node to $p$, and there is no subsequent
    use of $x + y$ after the last such placement.
    """

    earliest_sets: Dict[BasicBlock, set[Expression]] = _comp_earliest_sets(
        blocks,
        all_exprs,
        anticipated_exprs_analysis.in_states,
        available_exprs_analysis.in_states
    )
    postponable_expr_lattice = LCMPostponableExprSemilattice(all_exprs)
    postponable_expr_transfer_cluster = LCMPostponableExprTransferCluster(earliest_sets, e_use_sets)
    postponable_expr_analysis = DataFlowAnalysisFramework(
        cfg=cfg,
        lattice=postponable_expr_lattice,
        transfer=postponable_expr_transfer_cluster,
        direction='forward',
        init_value=postponable_expr_lattice.bottom(),
        safe_value=postponable_expr_lattice.top(),
        # on_state_change=expr_on_state_change
    )
    postponable_expr_analysis.analyze(strategy='worklist')


    """
    Step 4:
    A simple, final backward data-flow pass is used to eliminate assignments to temporary variables that
    are used only once in the program.
    """

    latest_sets: Dict[BasicBlock, set[Expression]] = _comp_latest_sets(
        blocks,
        cfg.successors,
        all_exprs,
        earliest_sets,
        postponable_expr_analysis.in_states,
        e_use_sets,
    )

    used_expr_lattice = LCMUsedExprSemilattice(all_exprs)
    used_expr_transfer_cluster = LCMUsedExprTransferCluster(
        e_use_set=e_use_sets,
        latest_set=latest_sets,
    )
    used_expr_analysis = DataFlowAnalysisFramework(
        cfg=cfg,
        lattice=used_expr_lattice,
        transfer=used_expr_transfer_cluster,
        direction='backward',
        init_value=used_expr_lattice.top(),
        safe_value=used_expr_lattice.top(),
        # on_state_change=expr_on_state_change
    )
    used_expr_analysis.analyze(strategy='worklist')



    """
    Lazy Code Motion Transformation
    """

    # Create a mapping from expressions to temporary variables.
    temp_vars = { }
    for i, expr in enumerate(all_exprs):
        # Generate unique temp var names
        temp_vars[expr] = f"{LCM_TMP_VAR_PREFIX}_{i}"

    # First pass:
    #
    # For all blocks $B$ such that $x + y$ is in $latest[B] \cap used[B].out$,
    # add $t = x + y$ at the beginning of B.

    blocks_exclude_entry = set(blocks) - {cfg.entry_block(), cfg.exit_block()}

    for block in blocks_exclude_entry:
        if block in latest_sets and latest_sets[block]:
            # Create new statement to insert
            for expr in latest_sets[block]:
                tv = temp_vars[expr]
                new_mir_inst = MIRInst(
                    offset=-1,
                    operand1=deepcopy(expr.operand1),
                    operand2=deepcopy(expr.operand2),
                    op=expr.op,
                    result=Operand(OperandType.VAR, Variable(tv))
                )
                block.insts.insert_insts(insts=new_mir_inst, index=0)
                insert_index = cfg.insts.index_for_inst(block.first_ordinary_inst)
                cfg.add_new_inst(insert_index, new_mir_inst)


    # Second pass:
    #
    # For all blocks $B$ such that $x + y$ is in
    # $$
    # e\_use_{B} \cap ( \neg latest[B] \cup used[B].out)
    # $$
    # replace every original x + y by t.

    for block in blocks_exclude_entry:
        for statement in block.insts.ret_insts():

            if not statement.is_arithmetic():
                continue

            dest_var: Variable = statement.result.value

            # Check if this statement computes any of our expressions
            replaced = False
            for expr in all_exprs:
                tv = temp_vars[expr]

                if has_expr(statement, expr) and tv != dest_var.varname:

                    # This statement computes the expression
                    # Replace with temporary variable.
                    convert_bin_expr_to_operand(
                        statement,
                        Operand(OperandType.VAR, Variable(tv)))
                    break

    cfg.reassign_inst_id()