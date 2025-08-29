from collections import deque
from typing import Dict, List, Tuple

from cof.base.mir.eval import mir_eval
from cof.base.mir.inst import MIRInstId, MIRInst, MIRInsts
from cof.base.mir.operand import Operand
from cof.base.ssa import SSAEdgeBuilder, SSAVariable
from cof.base.cfg import ControlFlowGraph, FlattenBasicBlocks
from cof.base.semilattice import ConstLattice


class SCCPAnalyzer:
    def __init__(self, cfg: ControlFlowGraph, ssa_builder: SSAEdgeBuilder):
        self.cfg: ControlFlowGraph = cfg
        self.ssa_builder: SSAEdgeBuilder = ssa_builder

        # exec_flag[(a, b)] records whether flowgraph edge a -> b is executable.
        self.exec_flag: Dict[Tuple[MIRInstId, MIRInstId], bool] = { }
        # lat_cell[ssa_v] records ConstLattice which relates ssa_v in the exit
        # of the node defined SSAVariable ssa_v
        self.lat_cell: Dict[str, ConstLattice] = { }

        self.flow_wl: deque[Tuple[MIRInstId, MIRInstId]] = deque()
        self.ssa_wl: deque[Tuple[MIRInstId, MIRInstId]] = deque()

        self.fatten_blocks: FlattenBasicBlocks = FlattenBasicBlocks(cfg)
        self._build()

    # ++++++++ Run ++++++++
    def _build(self):
        self.fatten_blocks.flatten_blocks()

    def initialize(self):
        first_inst_id = self.cfg.insts.ret_inst_by_idx(0).id
        self.flow_wl.append((first_inst_id, self.flow_succ(first_inst_id)[0]))

        for p in self.fatten_blocks.edges:
            self.exec_flag[p[0], p[1]] = False

        for i in self.cfg.insts.ret_insts():
            if i.is_assignment():
                self.lat_cell[str(i.result.value)] = ConstLattice()

    def run(self):
        while self.flow_wl or self.ssa_wl:
            if self.flow_wl:
                e = self.flow_wl.popleft()
                b = e[1]

                # Propagate constants along flowgraph edges
                if not self.exec_flag[e]:
                    self.exec_flag[e] = True
                    if self.inst(b).is_phi():
                        self.visit_phi(self.inst(b))

                    elif self.edge_count(b, self.fatten_blocks.edges) == 1:
                        self.visit_inst(b, self.inst(b), self.fatten_blocks.exec_flow)

            # Propagate constants along ssa edges
            # Handling the dependency relationship between variables. When the
            # value of a variable changes(for example, from TOP to a constant 5),
            # all instructions that directly depend on the variable(i.e. instructions
            # that use the variable) are added to ssa_wl to recalculate the values of
            # these instructions.
            if self.ssa_wl:
                e = self.ssa_wl.popleft()
                b = e[1]

                if self.inst(b).is_phi():
                    self.visit_phi(self.inst(b))
                elif self.edge_count(b, self.fatten_blocks.edges) >= 1:
                    self.visit_inst(b, self.inst(b), self.fatten_blocks.exec_flow)


    # ++++++++ Helper ++++++++
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

    def inst(self, mir_id: MIRInstId) -> MIRInst:
        return self.cfg.insts_dict_by_id[mir_id]

    def get_insts(self) -> MIRInsts:
        return self.cfg.insts

    # +++++++ Eval +++++++
    def lat_eval(self, inst: MIRInst) -> ConstLattice:
        """
        If inst is call, phi or anything else that can't directly evaluatable,
        we set c.state TOP and return it. This way be called conservative handing.
        Because optimizer can't determine the side effects of the callee. So
        optimizer will assume that the callee may modify any global variables and
        return arbitrary result.

        But if the callee is pure function(no side effects and only depends
        on input parameters)or is marked pure function by IR generator, then
        we can evaluate it.

        And if inst is assignment or if that can evaluatable, we will use
        constant folding techniques to optimize.

        :param inst: any mir insts
        :return: a constant lattice
        """



        top_const_lat: ConstLattice = ConstLattice()

        if not inst.is_evaluatable():
            return top_const_lat

        operand_list: List[Operand] = inst.ret_a_operand_list_for_evaluatable_exp_inst()
        op_cl_list: List[ConstLattice] = [ ]
        for o in operand_list:
            if isinstance(o.value, SSAVariable):
                op_cl = self.lat_cell[str(o.value)]
                op_cl_list.append(op_cl)
            else:
                op_cl = ConstLattice.constant(o)
                op_cl_list.append(op_cl)

        # two operands are constant.
        if len(operand_list) == 2 and (op_cl_list[0].value and op_cl_list[1].value):
            result = mir_eval(inst.op, op_cl_list[0].value, op_cl_list[1].value)
            return ConstLattice.constant(result)
        elif len(op_cl_list) == 1 and op_cl_list[0].value:
            return op_cl_list[0]

        return top_const_lat

    def visit_phi(self, inst: MIRInst):
        """ process phi node """
        var_list = inst.ret_operand_list()
        new_value = ConstLattice()
        for var in var_list:
            new_value ^= (self.lat_cell[str(var.value)])

        if new_value != self.lat_cell[str(inst.result.value)]:
            self.lat_cell[str(inst.result.value)] ^= new_value

            for succ_id in self.flow_succ(inst.id):
                self.flow_wl.append((inst.id, succ_id))
            for user in self.ssa_succ(inst.id):
                self.ssa_wl.append((inst.id, user))


    def visit_inst(self, k: MIRInstId, inst: MIRInst, exec_flow: Dict[Tuple[MIRInstId, MIRInstId], bool]):
        if inst.is_assignment():
            target: str = str(inst.result.value)
        elif inst.is_if() and inst.operand1.is_ssa_var():
            target: str = str(inst.operand1.value)
        else:
            succ = self.flow_succ(k)
            if succ:
                self.flow_wl.append((k, succ[0]))
            return

        val: ConstLattice = self.lat_eval(inst)

        # Handling the dependency relationship between variables. When the
        # value of a variable changes(for example, from TOP to a constant 5),
        # all instructions that directly depend on the variable(i.e. instructions
        # that use the variable) are added to ssa_wl to recalculate the values of
        # these instructions.
        if val != self.lat_cell[target]:
            self.lat_cell[target] ^= val

            for succ_id in self.ssa_succ(inst.id):
                self.ssa_wl.append((inst.id, succ_id))


        k_succ_edges_set = self.flow_succ_edge(k)

        if val.is_top:
            for succ_edge in k_succ_edges_set:
                self.flow_wl.append(succ_edge)

        elif not val.is_bottom:
            """ constant """
            if len(k_succ_edges_set) == 2:
                for succ_edge in k_succ_edges_set:
                    if (val.is_cond_true and exec_flow[succ_edge] == True) \
                        or (not val.is_cond_true and exec_flow[succ_edge] == False):
                        self.flow_wl.append(succ_edge)

            elif len(k_succ_edges_set) == 1:
                self.flow_wl.append(k_succ_edges_set.pop())





def sccp_analysis(cfg: ControlFlowGraph, ssa_builder: SSAEdgeBuilder) -> SCCPAnalyzer:
    sccp_optimizer = SCCPAnalyzer(cfg, ssa_builder)
    sccp_optimizer.initialize()
    sccp_optimizer.run()

    return sccp_optimizer