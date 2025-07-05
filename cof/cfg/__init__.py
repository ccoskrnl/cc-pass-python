import random
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

        # [(src_id, dst_id), (src_Id, dst_id)]
        self.edges: List[Tuple] = []

        # predecessors
        self.pred = defaultdict(list)
        # successors
        self.succ = defaultdict(list)
        # dominators
        self.dom: Dict[int, set] = {}
        # immediate dominators
        self.idom: Dict[int, int] = {}

        self.post_order: List[int] = [ ]

        self.__built__()

    def post_order_comp(self):
        """
        Post-Order
        :return:
        """

        # build children map from idom
        children = defaultdict(list)
        for node in self.vertex_ids_set:
            parent = self.idom[node]
            if parent != -1:
                children[parent].append(node)

        root = self.root.id

        # iterative post-order traversal
        stack = [(root, False)]
        visited = set()

        while stack:
            node, is_visited = stack.pop()
            if is_visited:
                self.post_order.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            stack.append((node, True))

            for child in reversed(children[node]):
                stack.append((child, False))

    def dom_comp(self):
        """
        A simple approach to computing all the dominators of each node in a flowgraph.
        :return:
        """
        # The algorithm first initializes change = True,
        change = True
        # dominators[root_id] = { root_id }
        root_id = self.root.id
        self.dom[root_id].add(root_id)
        # and dominators[i] = { all vertex ids } for each vertex i other than root.
        for n in self.vertex_ids_set - {root_id}:
            self.dom[n].update(self.vertex_ids_set)

        while change:
            change = False

            for n in self.vertex_ids_set - {root_id}:
                tmp_dominator_set = set(self.vertex_ids_set)

                # For first iteration, p is root_id ( the only member of Pred(B1) )
                # and so set tmp_dominator_set = { root_id }
                for p in self.pred[n]:
                    tmp_dominator_set &= self.dom[p]

                dominator_set = { n } | tmp_dominator_set
                if dominator_set != self.dom[n]:
                    change = True
                    self.dom[n] = dominator_set

    def idom_comp(self):
        """
        In essence, the algorithm first sets tmp[i] to dom[i] - { i }
        and then checks for each vertex i whether each element in tmp[i]
        has dominators other than itself and, if so, remove them from tmp[i].
        :return:
        """
        root_id = self.root.id
        tmp = {i: set() for i in range(self.n_bbs)}
        new_tmp = {i: set() for i in range(self.n_bbs)}

        for n in self.vertex_ids_set:
            tmp[n] = self.dom[n] - { n }
            new_tmp[n] = self.dom[n] - { n }

        for n in self.vertex_ids_set - { root_id }:
            for s in tmp[n]:
                for t in tmp[n] - { s }:
                    if t in tmp[s]:
                        new_tmp[n] -= { t }

        for n in self.vertex_ids_set - { root_id }:
            self.idom[n] = random.choice(list(new_tmp[n]))

    def construct_cfg(self):

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

        for (src, dst) in self.edges:
            self.succ[src].append(dst)
            self.pred[dst].append(src)

        # Add predecessors and successors for all basic blocks.
        # iterate all vertices
        for k, v in self.vertices.items():
            # get all predecessors from self.predecessors[k]
            for n in self.pred[k]:
                v.pred_bbs[n] = self.vertices[n]
            # get all successors from self.successors[k]
            for n in self.succ[k]:
                v.succ_bbs[n] = self.vertices[n]

    def __built__(self):
        self.construct_cfg()

        # dominators
        self.dom: Dict[int, set] = {i: set() for i in range(self.n_bbs)}
        # immediate dominators
        self.idom: Dict[int, int] = {i: -1 for i in range(self.n_bbs)}

        self.dom_comp()
        self.idom_comp()
        self.post_order_comp()