from typing import Dict, List, Tuple

from cof.analysis.ssa import SSAEdgeBuilder, SSAVariable
from cof.cfg import ControlFlowGraph, FlattenBasicBlocks
from cof.cfg.bb import BasicBlockId, BranchType
from cof.ir.lattice import ConstLattice
from cof.ir.mir import MIRInst, OperandType, MIRInstId, Operand, mir_eval


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
        self._build()

    def _build(self):
        self.fatten_blocks.flatten_blocks()

    def run(self):
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
                        self.visit_inst(b, self.inst(b), self.fatten_blocks.exec_flow)

            # propagate constants along ssa edges
            if self.ssa_wl:
                e = self.ssa_wl.pop()
                # a = e[0]
                b = e[1]

                if self.inst(b).is_phi():
                    self.visit_phi(self.inst(b))
                elif self.edge_count(b, self.fatten_blocks.edges) >= 1:
                    self.visit_inst(b, self.inst(b), self.fatten_blocks.exec_flow)

    def flow_succ_edge(self, mir_id: MIRInstId) -> set[Tuple[MIRInstId, MIRInstId]]:
        s = set()
        succ_inst_id_list = self.fatten_blocks.succ[mir_id]
        for succ in succ_inst_id_list:
            s.add((mir_id, succ))
        return s

    def flow_succ(self, mir_id: MIRInstId) -> List[MIRInstId]:
        return self.fatten_blocks.succ[mir_id]


    def ssa_succ_edge(self, mir_id: MIRInstId) -> set[Tuple[MIRInstId, MIRInstId]]:
        s = set()
        succ_inst_id_list = self.ssa_builder.succ[mir_id]
        for succ in succ_inst_id_list:
            s.add((mir_id, succ))
        return s

    def ssa_succ(self, mir_id: MIRInstId) -> List[MIRInstId]:
        return self.ssa_builder.succ[mir_id]

    def inst(self, mir_id: MIRInstId) -> MIRInst:
        return self.cfg.insts_dict_by_id[mir_id]

    def initialize(self):
        first_inst_id = self.cfg.insts.ret_inst_by_idx(0).id
        self.flow_wl = set()
        self.flow_wl.add((first_inst_id, self.flow_succ(first_inst_id).pop()))
        self.ssa_wl = set ()

        for p in self.fatten_blocks.edges:
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

        if not inst.is_evaluatable():
            return c

        operand_list: List[Operand] = inst.ret_operand_list_of_exp()
        op_cl_list: List[ConstLattice] = [ ]
        for o in operand_list:
            if isinstance(o.value, SSAVariable):
                op_cl = self.lat_cell[str(o.value)]
                op_cl_list.append(op_cl)
            else:
                op_cl: ConstLattice = ConstLattice()
                op_cl.set_constant(o)
                op_cl_list.append(op_cl)

        # two operands are constant.
        if len(operand_list) == 2 and (op_cl_list[0].value and op_cl_list[1].value):
            result = mir_eval(inst.op, op_cl_list[0].value, op_cl_list[1].value)
            c.set_constant(result)
        elif len(op_cl_list) == 1 and op_cl_list[0].value:
            return op_cl_list[0]
        else:
            for cl in op_cl_list:
                c &= cl
        return c

    def visit_phi(self, inst: MIRInst):
        """ process phi node """
        for var in inst.ret_operand_list():
            self.lat_cell[str(inst.result.value)] &= (self.lat_cell[str(var.value)])

    def visit_inst(self, k: MIRInstId, inst: MIRInst, exec_flow: Dict[Tuple[MIRInstId, MIRInstId], BranchType]):
        if inst.is_assignment():
            target: str = str(inst.result.value)
        elif inst.is_if() and inst.operand1.is_ssa_var():
            target: str = str(inst.operand1.value)
        else:
            return

        val: ConstLattice = self.lat_eval(inst)
        if val != self.lat_cell[target]:
            self.lat_cell[target] &= val
            self.ssa_wl |= self.ssa_succ_edge(inst.id)

        k_succ_edges_set = self.flow_succ_edge(k)

        if val.is_top():
            self.flow_wl |= k_succ_edges_set

        elif not val.is_bottom():
            """ constant """
            if len(k_succ_edges_set) == 2:
                for succ_edge in k_succ_edges_set:
                    if (val.is_cond_true() and exec_flow[succ_edge] == BranchType.TRUE) \
                        or (not val.is_cond_true() and exec_flow[succ_edge] == BranchType.FALSE):
                        self.flow_wl.add(succ_edge)

            elif len(k_succ_edges_set) == 1:
                self.flow_wl |= k_succ_edges_set




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
    optimizer.run()
    pass