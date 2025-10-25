from collections import defaultdict
from typing import Dict, Set, List, Tuple

from cof.analysis.dataflow import DataFlowAnalyzer
from cof.base.bb import BasicBlock, BasicBlockId, BasicBlockBranchType
from cof.base.cfg import ControlFlowGraphForDataFlowAnalysis, ControlFlowGraph
from cof.base.mir.inst import MIRInst
from cof.base.mir.operand import Operand, OperandType
from cof.base.mir.operator import Op
from cof.base.mir.variable import Variable, PHI_TMP_VAR_PREFIX
from cof.base.ssa import SSAVariable, SSAEdgeBuilder


class InterferenceGraph:

    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(set)  # node -> set of interfering nodes
        self.adjacency = defaultdict(set)  # adjacency list

    def add_node(self, node):
        self.nodes.add(node)
        self.edges[node] = set()
        self.adjacency[node] = set()

    def add_edge(self, node1, node2):
        if node1 != node2:
            self.edges[node1].add(node2)
            self.edges[node2].add(node1)
            self.adjacency[node1].add(node2)
            self.adjacency[node2].add(node1)

    def has_edge(self, node1, node2):
        return node2 in self.edges[node1]

    def degree(self, node):
        return len(self.edges[node])

    def remove_node(self, node):
        if node in self.nodes:
            for neighbor in list(self.adjacency[node]):
                self.adjacency[neighbor].discard(node)
                self.edges[neighbor].discard(node)

            self.nodes.discard(node)
            if node in self.edges:
                del self.edges[node]
            if node in self.adjacency:
                del self.adjacency[node]

def is_phi_assign_block(block: BasicBlock) -> bool:
        return True if block.comment[:12] == "[phi assign]" else False



def compute_live_range(cfg: ControlFlowGraphForDataFlowAnalysis, ) -> Dict[Variable, Set[BasicBlock]]:
    data_flow_analyzer = DataFlowAnalyzer(cfg=cfg)
    liveness_analysis_result = data_flow_analyzer.live_vars()
    live_ranges: Dict[Variable, Set[BasicBlock]] = {}
    for block in cfg.all_blocks():
        for var in liveness_analysis_result[block]:
            if var not in live_ranges:
                live_ranges[var] = set()
            live_ranges[var].add(block)

    return live_ranges


def build_interference_graph(
        cfg: ControlFlowGraph,
        live_ranges: Dict[Variable, Set[BasicBlock]]
) -> InterferenceGraph:
    interference_graph = InterferenceGraph()

    all_vars = set()
    # 1.    collect all ssa variables.
    for inst in cfg.insts.ret_insts():
        all_vars.update({inst.ret_def_var()})
        all_vars.update({inst.ret_use_var()})

    # 2.    add all variables as graph's node.
    for var in all_vars:
        interference_graph.add_node(var)

    # 3.    add conflict edges for variables that are simultaneously active
    #       in each basic block.
    for block in cfg.block_by_id.values():
        live_vars_in_block: Set[Variable] = set()
        for var, blocks in live_ranges.items():
            if var in blocks:
                live_vars_in_block.add(var)

        live_list: List[Variable] = list(live_vars_in_block)
        for i in range(len(live_list)):
            for j in range(i + 1, len(live_list)):
                var1, var2 = live_list[i], live_list[j]
                if var1.varname == var2.varname:
                    interference_graph.add_edge(var1, var2)

    return interference_graph


# def eliminate_phi_functions(cfg: ControlFlowGraph, ssa_edge_builder: SSAEdgeBuilder) -> Dict[SSAVariable, SSAVariable]:
#     phi_replacements = {}
#     critical_edge_splitter = CriticalEdgeSplitter(cfg=cfg, ssa_edge_builder=ssa_edge_builder)
#
#     def process_phi_function(phi_para: MIRInst):
#         nonlocal phi_replacements
#         phi_result: SSAVariable = phi_para.result.value
#         assert isinstance(phi_result, SSAVariable)
#
#         phi_tv_name = f"{PHI_TMP_VAR_PREFIX}_{phi_result.base_name}"
#         phi_tv = Variable(phi_tv_name, compiler_generated=True, scope=phi_result.scope)
#         phi_replacements[phi_result] = phi_tv
#
#     for basic_block in cfg.block_by_id.values():
#         for phi_instr in basic_block.insts.ret_phi_insts():
#             process_phi_function(phi_instr)
#             for predecessor in cfg.predecessors(basic_block.id):
#                 if critical_edge_splitter.is_critical_edge(predecessor.id, basic_block.id):
#
#                     # Create an intermediate block
#                     intermediate_block = critical_edge_splitter.split_single_edge(predecessor, basic_block)
#                     original_var = phi_instr.ret_var_by_pred_id_for_phi(predecessor.id)
#                     assert original_var is not None
#
#                     # create a copy instruction
#                     operand1 = Operand(OperandType.VAR, original_var)
#                     result = Operand(OperandType.VAR, phi_replacements[phi_instr.result.value])
#                     copy_inst = MIRInst(
#                         offset=0,
#                         op=Op.ASSIGN,
#                         operand1=operand1,
#                         operand2=None,
#                         result=result,
#                     )
#                     # insert the inst into the intermediate block.
#                     insert_index = cfg.insts.index_for_inst(basic_block.first_ordinary_inst)
#                     cfg.add_new_inst(insert_index, copy_inst)
#                     intermediate_block.insts.insert_insts(copy_inst, 0)
#
#                     # get the last instruction in predecessor.
#                     last_inst_in_pred = predecessor.insts.ret_inst_by_idx(-1)
#                     if last_inst_in_pred.is_if():
#                         # get the inst id of the true branch of this if inst.
#                         true_branch_inst_id = last_inst_in_pred.result.value
#                         true_branch_inst = basic_block.insts.inst_by_id(true_branch_inst_id)
#                         if true_branch_inst:
#                             # insert goto instruction into intermediate block
#                             last_inst_in_pred.result.value = copy_inst.unique_id
#                             goto_inst = MIRInst(
#                                 offset=0,
#                                 op=Op.GOTO,
#                                 result=basic_block.first_ordinary_inst.unique_id,
#                                 operand1=None,
#                                 operand2=None,
#                             )
#                             intermediate_block.insts.insert_insts(goto_inst, -1)
#                             cfg.add_new_inst(insert_index, goto_inst)
#
#                         else:
#
#                             pass
#                     # goto_inst = MIRInst(
#                     #     offset=0,
#                     #     op=Op.GOTO,
#                     # result=basic_block.insts.ret,
#                     # )
#
#     return {}


class SSADestroyer:
    def __init__(self, cfg: ControlFlowGraph, ssa_edge_builder: SSAEdgeBuilder):
        self.cfg = cfg
        self.ssa_edge_builder = ssa_edge_builder
        self.intermediate_blocks : Dict[BasicBlockId, BasicBlock] = dict()

    def destroy(self):
        block_with_phi: List[BasicBlock] = []
        for basic_block in self.cfg.block_by_id.values():
            if len(basic_block.insts.ret_phi_insts()) > 0:
                block_with_phi.append(basic_block)

        # split critical edge
        for phi_block in block_with_phi:
            for block_critical_edge in self.ret_block_critical_edge(phi_block):
                new_block = self.split_critical_edge(block_critical_edge)
                self.intermediate_blocks[new_block.id] = new_block


    def ret_block_critical_edge(self, block: BasicBlock) -> List[Tuple[BasicBlock, BasicBlock]]:
        critical_edges = []

        for pred_block_id in block.pred_bbs:
            # 1. src block has multiple successors.
            # 2. dst block has multiple predecessors.
            if len(self.cfg.successors(pred_block_id)) > 1 and len(self.cfg.predecessors(block.id)) > 1:
                critical_edges.append((block.pred_bbs[pred_block_id], block))

        return critical_edges

    def split_critical_edge(self, critical_edge: Tuple[BasicBlock, BasicBlock]) -> BasicBlock:
        intermediate_block = self.cfg.new_a_block(self.cfg.n_bbs, [])
        self.update_cfg_connection(intermediate_block, critical_edge[0], critical_edge[1])
        return intermediate_block


    def update_cfg_connection(self, intermediate_block: BasicBlock, src: BasicBlock, dst: BasicBlock):

        # add the intermediate block into cfg.
        self.cfg.block_id_set.add(intermediate_block.id)
        self.cfg.block_by_id[intermediate_block.id] = intermediate_block

        # add comment for this new allocated intermediate block.
        intermediate_block.comment = f"[phi assign] intermediate block from {src.id} to {dst.id}"

        # add new created edge for cfg.
        self.cfg.edges.append((src.id, intermediate_block.id))
        self.cfg.edges.append((intermediate_block.id, dst.id))

        # update the successors dict in intermediate block
        intermediate_block.succ_bbs[dst.id] = dst

        # update the predecessors of the dst block
        self.cfg.pred[dst.id].append(intermediate_block.id)
        self.cfg.pred[dst.id].remove(src.id)
        dst.pred_bbs[intermediate_block.id] = intermediate_block
        dst.pred_bbs.pop(src.id)

        # update the predecessors dict in intermediate block
        intermediate_block.pred_bbs[src.id] = src

        # update the successors of the src block
        self.cfg.succ[src.id].append(intermediate_block.id)
        self.cfg.succ[src.id].remove(dst.id)
        src.succ_bbs[intermediate_block.id] = intermediate_block
        src.succ_bbs.pop(dst.id)

        # Create goto inst and add the new inst into intermediate block.
        first_ordinary_inst = dst.first_ordinary_inst
        goto_inst = MIRInst(
            offset=0,
            op=Op.GOTO,
            result=first_ordinary_inst.unique_id,
            operand1=None,
            operand2=None,
        )

        intermediate_block.insts.insert_insts(goto_inst, -1)

        # insert the new inst into cfg's insts based on the src block branch type.
        if src.branch_type == BasicBlockBranchType.cond:

            cond_branch = src.insts.ret_inst_by_idx(-1)

            if dst.id == src.ordered_succ_bbs[0]:
                # True branch
                insert_index = self.cfg.insts.index_for_inst(dst.first_ordinary_inst)

                # insert the goto inst before the dst's first ordinary inst in the cfg inst sequence.
                self.cfg.add_new_inst(insert_index, goto_inst)

                # update true branch target
                cond_branch.result.value = goto_inst.unique_id

            elif dst.id == src.ordered_succ_bbs[1]:
                # False branch
                insert_index = self.cfg.insts.index_for_inst(cond_branch)

                # insert the goto inst after the src conditional branch instruction in the cfg inst sequence.
                self.cfg.add_new_inst(insert_index + 1, goto_inst)

            else:
                assert False
        # we don't handle the switch type, because up to now, we haven't used this branch type yet.
        elif src.branch_type == BasicBlockBranchType.switch:
            pass

        # if the branch type is jump, it is impossible to generate a critical edge, so we need to throw an exception.
        else:
            raise "jump branch type can't generated a critical edge!"

        self.cfg.reassign_inst_id()
