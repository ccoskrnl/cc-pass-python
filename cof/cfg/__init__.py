from collections import defaultdict
from typing import Tuple, Dict
from ..ir import *
from .bb import *

class ControlFlowGraph:
    def __init__(self, insts: Insts):
        # Instruction List
        self.insts = insts

        # The root of the cfg
        self.root = None
        # The number of basic blocks
        self.n_bbs: int = 0
        self.vertex_ids_set = set()
        self.vertices: Dict[int, BasicBlock] = { }
        self.edges: List[Tuple] = []

        self.predecessors = defaultdict(list)
        self.successors = defaultdict(list)

        self.construct()

        for (src, dst) in self.edges:
            self.successors[src].append(dst)
            self.predecessors[dst].append(src)

        # Add predecessors and successors for all basic blocks.
        # iterate all vertices
        for k, v in self.vertices.items():
            # get all predecessors from self.predecessors[k]
            for n in self.predecessors[k]:
                v.pred_bbs[n] = self.vertices[n]
            # get all successors from self.successors[k]
            for n in self.successors[k]:
                v.succ_bbs[n] = self.vertices[n]





    def construct(self):

        # The Set type guarantees that there are no identical elements.
        leaders_set = set()

        for inst_idx in range(0, self.insts.num):
            inst = self.insts.ir_insts[inst_idx]

            match inst.op:

                case Op.ENTRY:
                    leaders_set.add(inst_idx)
                    leaders_set.add(inst_idx + 1)

                case Op.EXIT:
                    leaders_set.add(inst_idx)

                case Op.IF:
                    leaders_set.add(inst_idx + 1)
                    assert inst.result.type == OperandType.ADDR
                    target = int(inst.result.value)
                    leaders_set.add(target)

                case Op.GOTO:
                    leaders_set.add(inst_idx + 1)
                    assert inst.result.type == OperandType.ADDR
                    target = int(inst.result.value)
                    leaders_set.add(target)

        # Constructing Basic Blocks and updating class members
        sorted_list = sorted(leaders_set)
        for leader_idx in range(0, len(sorted_list) - 1):
            bb_id = self.n_bbs
            src_vertex = BasicBlock(bb_id, sorted_list[leader_idx], sorted_list[leader_idx+1], self.insts)
            self.vertices[bb_id] = src_vertex
            self.vertex_ids_set.add(bb_id)
            self.n_bbs += 1

        # Construct the exit basic block
        bb_id = self.n_bbs
        src_vertex = BasicBlock(bb_id, sorted_list[-1], self.insts.num, self.insts)
        self.vertices[bb_id] = src_vertex
        self.vertex_ids_set.add(bb_id)
        self.n_bbs += 1

        self.root = self.vertices[0]

        # Updating Edges in the CFG
        for src_vertex in self.vertices.values():

            # Get the last inst in basic block.
            last_inst_idx = src_vertex.inst_idx_list[-1]
            last_inst = src_vertex.insts[-1]

            # Handling GOTO statement
            if last_inst.op == Op.GOTO:
                target_inst_idx = int(last_inst.result.value)
                dst_vertex = next((target_bb \
                                   for target_bb in self.vertices.values() \
                                   if target_bb.inst_exist(target_inst_idx)))

                # record the next bb
                src_vertex.branch_type = BasicBlockBranchType.jump
                src_vertex.ordered_succ_bbs.append(dst_vertex.id)

                self.edges.append((src_vertex.id, dst_vertex.id))

            else:

                # Handle IF
                if last_inst.op == Op.IF:
                    target_inst_idx = int(last_inst.result.value)
                    dst_vertex = next((target_bb \
                                       for target_bb in self.vertices.values() \
                                       if target_bb.inst_exist(target_inst_idx)))
                    src_vertex.branch_type = BasicBlockBranchType.cond
                    src_vertex.ordered_succ_bbs.append(dst_vertex.id)
                    self.edges.append((src_vertex.id, dst_vertex.id))
                else:
                    src_vertex.branch_type = BasicBlockBranchType.jump

                dst_vertex = next((target_bb \
                                   for target_bb in self.vertices.values() \
                                   if target_bb.inst_exist(last_inst_idx + 1)), -1)

                if dst_vertex != -1:
                    src_vertex.ordered_succ_bbs.append(dst_vertex.id)
                    self.edges.append((src_vertex.id, dst_vertex.id))




