from typing import Dict, List, Tuple

from cof.analysis.ssa import SSAEdgeBuilder, SSAVariable
from cof.cfg import ControlFlowGraph, FlattenBasicBlocks
from cof.cfg.bb import BasicBlockId, BranchType
from cof.ir.lattice import ConstLattice
from cof.ir.mir import MIRInst, OperandType, MIRInstId


class SCCPOptimizer:
    def __init__(self, cfg: ControlFlowGraph, ssa_builder: SSAEdgeBuilder):
        self.cfg: ControlFlowGraph = cfg
        self.ssa_builder: SSAEdgeBuilder = ssa_builder

        # exec_flag[(a, b)] records whether flowgraph edge a -> b is executable.
        self.exec_flag: Dict[Tuple[BasicBlockId, BasicBlockId], bool] = { }
        # lat_cell[ssa_v] records ConstLattice which relates ssa_v in the exit
        # of the node defined SSAVariable ssa_v
        self.lat_cell: Dict[str, ConstLattice] = { }

        self.flow_wl: set[Tuple[MIRInstId, MIRInstId]] = set()
        self.ssa_wl: set[Tuple[MIRInstId, MIRInstId]] = set()

        self.fatten_blocks: FlattenBasicBlocks = FlattenBasicBlocks(cfg)

    def _build(self):
        self.fatten_blocks.flatten_blocks()

    def run(self):
        self.initialize()
        while self.flow_wl or self.ssa_wl:
            if self.flow_wl:
                e = self.flow_wl.pop()
                # a = e[0]
                b = e[1]

                # propagate constants along flowgraph edges
                if not self.exec_flag[e]:
                    self.exec_flag[e] = True
                    if self.inst(b).is_phi():
                        self.visit_phi(self.inst(b))

                    elif self.edge_count(b, self.fatten_blocks.edges) == 1:
                        self.visit_inst(b, self.inst(b), self.cfg.exec_flow)

            # propagate constants along ssa edges
            if self.ssa_wl:
                e = self.ssa_wl.pop()
                # a = e[0]
                b = e[1]

                if self.inst(b).is_phi():
                    self.visit_phi(self.inst(b))
                elif self.edge_count(b, self.fatten_blocks.edges) >= 1:
                    self.visit_inst(b, self.inst(b), self.cfg.exec_flow)

    def flow_succ(self, mir_id: MIRInstId) -> List[MIRInstId]:
        return self.fatten_blocks.succ[mir_id]

    def ssa_succ(self, mir_id: MIRInstId) -> List[MIRInstId]:
        return self.ssa_builder.succ[mir_id]

    def inst(self, mir_id: MIRInstId) -> MIRInst:
        return self.cfg.insts_dict_by_id[mir_id]

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
            elif operand.is_const():
                para: ConstLattice = ConstLattice()
                para.set_constant(operand.value, operand.type)

        return c

    def visit_phi(self, inst: MIRInst):
        """ process phi node """
        for var in inst.ret_operand_list():
            self.lat_cell[str(inst.result.value)] &= (self.lat_cell[str(var.value)])

    def visit_inst(self, k: MIRInstId, inst: MIRInst, exec_flow: Dict[Tuple[MIRInstId, MIRInstId], BranchType]):
        if inst.is_assignment():
            target: str = str(inst.result.value)
        elif inst.is_if() and inst.operand1 == OperandType.SSA_VAR:
            target: str = str(inst.operand1.value)
        else:
            return

        val: ConstLattice = self.lat_eval(inst)
        if val != self.lat_cell[target]:
            self.lat_cell[target] &= val
            self.ssa_wl |= self.ssa_succ(inst.id)

        succ_k_list = self.flow_succ(k)

        if val.is_top():
            for i in succ_k_list:
                self.flow_wl |= (k, i)

        elif not val.is_bottom():
            """ constant """
            if len(succ_k_list) == 2:
                for i in succ_k_list:
                    if (val.is_cond_true() and exec_flow[(k, i)] == BranchType.TRUE) \
                        or (not val.is_cond_true() and exec_flow[(k, i)] == BranchType.FALSE):
                        self.flow_wl |= (k, i)

            elif len(succ_k_list) == 1:
                self.flow_wl |= (k, succ_k_list[0])




    def edge_count(self, b: MIRInstId, edges: List[Tuple[MIRInstId, MIRInstId]]) -> int:
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