from collections import defaultdict
from typing import Dict, Tuple, List

from cof.base.bb import BasicBlockId
from cof.base.mir.args import Args
from cof.base.mir.inst import MIRInst, MIRInstId
from cof.base.mir.operand import Operand, OperandType
from cof.base.mir.operator import Op
from cof.base.mir.variable import Variable


class SSAVariable(Variable):
    __slots__ = ('version', 'original_variable', 'block_id')

    def __init__(self, var: Variable, version: int = -1, block_id : int = -1):
        # 调用父类初始化
        super().__init__(var.varname)
        # self.varname = var.varname if isinstance(var, Variable) else var
        self.version : int= version
        self.original_variable: Variable = var
        self.block_id : BasicBlockId = -1

    def __str__(self):
        return f"{self.varname}#{self.version}"

    @property
    def base_name(self) -> str:
        return self.varname

    def __hash__(self):
        return hash((self.original_variable, self.version))
    def __eq__(self, other : 'SSAVariable'):
        return self.original_variable == other.original_variable and self.version == other.version

    def __copy__(self):
        return SSAVariable(self.original_variable, self.version, self.block_id)

class SSAEdge:
    """
    def-use chain
    """
    __slots__ = ('source_inst', 'target_inst', 'src_block', 'dest_block', 'var', 'type', 'loop_carried')

    def __init__(self, source_inst: MIRInst, target_inst: MIRInst, src_block, dest_block, var):
        # def
        self.source_inst: MIRInst = source_inst
        # use
        self.target_inst: MIRInst = target_inst

        self.src_block = src_block
        self.dest_block = dest_block

        self.var = var

        # REGULAR / PHI_ARG / LOOP_CARRIED

        # Regular Edge: The most common def-use chain. It represents the conventional
        #   definition and usage relationship of variables whin a basic block or across basic blocks.

        # Phi Arg Edge: connecting the definition of phi arguments with phi function.

        # Loop Carried Edge: It represents the data dependency relationship between loop iterations.
        #   Definition points and usage points in different loop iterations. The source_inst defines the
        #   value in the current iteration of the loop. The value is used in the next iteration of the
        #   loop by target_inst. And usually related to the phi function.
        self.type = "REGULAR"
        self.loop_carried = False

    @property
    def id(self) -> Tuple[MIRInstId, MIRInstId]:
        return self.source_inst.unique_id, self.target_inst.unique_id

    def mark_loop_carried(self):
        self.type = "LOOP_CARRIED"
        self.loop_carried = True

    def __repr__(self):
        edge_type = self.type if self.type != "REGULAR" else ""
        return f"MIR[ {self.source_inst} ]    ->    MIR[ {self.target_inst} ]    VAR[ {self.var} ]    {edge_type} "


class SSAEdgeBuilder:
    def __init__(self, cfg, edges: List[SSAEdge], def_map):
        self.cfg = cfg
        self.ssa_edge_list: List[SSAEdge] = edges
        self.edges: List[Tuple[MIRInstId, MIRInstId]] = self._collect_ssa_edge()
        self.succ: Dict[MIRInstId, List[MIRInstId]] = self._construct_ssa_succ()
        self.def_map = def_map

    def _construct_ssa_succ(self) -> Dict[MIRInstId, List[MIRInstId]]:
        succ: Dict[MIRInstId, List[MIRInstId]] = defaultdict(list)
        for s,d in self.edges:
            succ[s].append(d)
        return succ

    def _collect_ssa_edge(self) -> List[Tuple[MIRInstId, MIRInstId]]:
        edges: List[Tuple[MIRInstId, MIRInstId]] = []

        for e in self.ssa_edge_list:
            edges.append(e.id)

        return edges


def create_phi_function(var: Variable, num_pred_s: int) -> MIRInst:
    args: List[Operand] = []
    for i in range(0, num_pred_s):
        args.append(Operand(OperandType.SSA_VAR, SSAVariable(var)))

    return MIRInst(
        offset=-1,
        op=Op.PHI,
        operand1=Operand(OperandType.VAR, Variable("φ")),
        operand2=Operand(OperandType.ARGS, Args(args)),
        result=Operand(OperandType.SSA_VAR, SSAVariable(var)),
    )


def has_phi_for_var(block, var: Variable) -> bool:
    # iterate all insts
    for phi_inst in block.insts.ret_phi_insts():
        result: SSAVariable = phi_inst.result.value
        if result.original_variable == var:
            return True
    return False
