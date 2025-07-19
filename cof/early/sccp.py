from typing import Dict, List, Tuple

from cof.analysis.ssa import SSAEdgeBuilder, SSAVariable, SSAEdge
from cof.cfg import ControlFlowGraph, BasicBlockId
from cof.ir.lattice import ConstLattice
from cof.ir.mir import MIRInst, OperandType


class SCCPOptimizer:
    def __init__(self, cfg: ControlFlowGraph, ssa_builder: SSAEdgeBuilder):
        self.cfg: ControlFlowGraph = cfg
        self.ssa_builder: SSAEdgeBuilder = ssa_builder

        # exec_flag[(a, b)] records whether flowgraph edge a -> b is executable.
        self.exec_flag: Dict[Tuple[BasicBlockId, BasicBlockId], bool] = { }
        # lat_cell[ssa_v] records ConstLattice which relates ssa_v in the exit
        # of the node defined SSAVariable ssa_v
        self.lat_cell: Dict[str, ConstLattice] = { }

        self.flow_wl: set[Tuple[BasicBlockId, BasicBlockId]] = set()
        self.ssa_wl: set[SSAEdge] = set()

    def initialize(self):
        self.flow_wl = [e for e in self.cfg.edges if e == self.cfg.root.id]
        self.ssa_wl = [ ]

        for p in self.cfg.edges:
            self.exec_flag[p[0], p[1]] = False

        for i in self.cfg.insts.ret_insts():
            if i.is_assignment():
                self.lat_cell[str(i.result.value)] = ConstLattice()

    def lat_eval(self, inst: MIRInst) -> ConstLattice:
        """
        1. if inst is a call or phi, operand_list is empty list.
        the c is top.
        2. if inst is a direct evaluatable inst, we can evaluate c,
        then return it.

        :param inst: any mir insts
        :return: a constant lattice
        """
        c: ConstLattice = ConstLattice()
        for operand in inst.ret_operand_list_of_exp():
            if isinstance(operand.value, SSAVariable):
                c &= self.lat_cell[str(operand.value)]

        return c

    def visit_phi(self, inst: MIRInst):
        """ process phi node """
        for var in inst.ret_operand_list():
            self.lat_cell[str(inst.result.value)] &= (self.lat_cell[str(var.value)])

    def visit_inst(self, k: BasicBlockId, inst: MIRInst):
        if inst.is_assignment():
            target: str = str(inst.result.value)
        elif inst.is_if() and inst.operand1 == OperandType.SSA_VAR:
            target: str = str(inst.operand1.value)
        else:
            return

        val: ConstLattice = self.lat_eval(inst)
        if val != self.lat_cell[target]:
            self.lat_cell[target] &= val
            self.ssa_wl |= self.ssa_builder.succ[inst]

        succ_k_list = self.cfg.succ[k]

        # if val.is_top():
        #     for i in succ_k_list:
        #         self.flow_wl |= (k, i)
        # elif not val.is_bottom():
        #     if len(succ_k_list) == 2:
        #         for i in succ_k_list:
        #             if




    def edge_count(self, b: BasicBlockId, edges: List[Tuple[BasicBlockId, BasicBlockId]]) -> int:
        """
        return number of executable flowgraph edges leading to b

        :param b:
        :param edges:
        :return:
        """
        i: int = 0
        for e in edges:
            if e[1] == b and self.exec_flag[e]:
                i += 1

        return i


def sccp_optimize(cfg: ControlFlowGraph, ssa_builder: SSAEdgeBuilder):
    optimizer = SCCPOptimizer(cfg, ssa_builder)
    optimizer.initialize()