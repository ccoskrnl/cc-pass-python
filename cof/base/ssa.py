from collections import defaultdict
from typing import Dict, Tuple, Union, Optional, List

from cof.base.mir.args import Args
from cof.base.mir.inst import MIRInst, MIRInstId
from cof.base.mir.operand import Operand, OperandType
from cof.base.mir.operator import Op
from cof.base.mir.variable import Variable


class SSAVariable:
    __slots__ = ('name', 'version')

    def __init__(self, var: Union[str, Variable], version: Optional[int]):
        self.name = var.varname if isinstance(var, Variable) else var
        self.version = version if version is not None else -1

    def __str__(self):
        return f"{self.name}#{self.version}"

    @property
    def base_name(self) -> str:
        return self.name


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
        self.type = "REGULAR"
        self.loop_carried = False

    @property
    def id(self) -> Tuple[MIRInstId, MIRInstId]:
        return self.source_inst.id, self.target_inst.id

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


def create_phi_function(varname: str, num_pred_s: int) -> MIRInst:
    args: List[Operand] = []
    for i in range(0, num_pred_s):
        args.append(Operand(OperandType.SSA_VAR, SSAVariable(varname, None)))

    return MIRInst(
        offset=-1,
        op=Op.PHI,
        operand1=Operand(OperandType.VAR, Variable("φ")),
        operand2=Operand(OperandType.ARGS, Args(args)),
        result=Operand(OperandType.SSA_VAR, SSAVariable(varname, None)),
    )


def has_phi_for_var(block, varname) -> bool:
    # iterate all insts
    for phi_inst in block.insts.ret_phi_insts():
        result: SSAVariable = phi_inst.result.value
        if result.base_name == varname:
            return True
    return False
