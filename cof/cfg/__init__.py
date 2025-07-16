import random
from collections import deque
from typing import Tuple, Dict
from .bb import *
from ..ssa import *

class ControlFlowGraph:
    def __init__(self, insts: MIRInsts):
        # Instruction List
        self.insts: MIRInsts = insts

        # The root of the cfg
        self.root = None
        # The number of basic blocks
        self.n_bbs: int = 0
        self.block_id_set = set()
        self.blocks: Dict[int, BasicBlock] = { }

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

        # Dominance Frontier
        self.df: Dict[int, set] = {}
        self.dfp: set = set()

        self.__built__()

    def dom_front(self):
        """
        Dominance Frontier
        :return:
        """
        df: Dict[int, set] = { i: set() for i in range(self.n_bbs)}

        for i in self.post_order:
            # Compute local component
            for y in self.succ[i]:
                if self.idom[y] != i:
                    df[i] |= {y}
            # Add on up component
            z = self.idom[i]
            if z != -1:
                for y in df[z]:
                    if y != self.idom[i]:
                        df[i] |= {y}
        self.df = df

    def df_plus(self, sn):
        """
        iterated dominance frontier DF+()
        :param sn:
        :return:
        """

        def df_set(s: set):
            dn = set()
            for x in s:
                dn |= self.df[x]
            return dn

        # d: set = set()
        change = True
        self.dfp = df_set(sn)
        while change:
            change = False
            d = df_set(sn | self.dfp)
            if d != self.dfp:
                self.dfp = d
                change = True

    def post_order_comp(self):
        """
        Post-Order
        :return:
        """

        # build children map from idom
        children = defaultdict(list)
        for node in self.block_id_set:
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

        # dominators
        self.dom: Dict[int, set] = {i: set() for i in range(self.n_bbs)}

        # The algorithm first initializes change = True,
        change = True
        # dominators[root_id] = { root_id }
        root_id = self.root.id
        self.dom[root_id].add(root_id)
        # and dominators[i] = { all vertex ids } for each vertex i other than root.
        for n in self.block_id_set - {root_id}:
            self.dom[n].update(self.block_id_set)

        while change:
            change = False

            for n in self.block_id_set - {root_id}:
                tmp_dominator_set = set(self.block_id_set)

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

        # immediate dominators
        self.idom: Dict[int, int] = {i: -1 for i in range(self.n_bbs)}

        root_id = self.root.id
        tmp = {i: set() for i in range(self.n_bbs)}
        new_tmp = {i: set() for i in range(self.n_bbs)}

        for n in self.block_id_set:
            tmp[n] = self.dom[n] - { n }
            new_tmp[n] = self.dom[n] - { n }

        for n in self.block_id_set - {root_id}:
            for s in tmp[n]:
                for t in tmp[n] - { s }:
                    if t in tmp[s]:
                        new_tmp[n] -= { t }

        for n in self.block_id_set - {root_id}:
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
            src_vertex = BasicBlock(bb_id, self.insts.ret_insts_by_pos(sorted_list[leader_idx], sorted_list[leader_idx+1]))
            self.blocks[bb_id] = src_vertex
            self.block_id_set.add(bb_id)
            self.n_bbs += 1

        # Construct the exit basic block
        bb_id = self.n_bbs
        src_vertex = BasicBlock(bb_id, self.insts.ret_insts_by_pos(sorted_list[-1], self.insts.num))
        self.blocks[bb_id] = src_vertex
        self.block_id_set.add(bb_id)
        self.n_bbs += 1

        self.root = self.blocks[0]

        # Updating Edges in the CFG
        for src_vertex in self.blocks.values():

            # Get the last inst in basic block.
            last_inst = src_vertex.insts.ret_inst_by_idx(-1)
            last_inst_idx = last_inst.addr

            # Handling GOTO statement
            if last_inst.op == Op.GOTO:
                target_inst_idx = int(last_inst.result.value)
                dst_vertex = next((target_bb \
                                   for target_bb in self.blocks.values() \
                                   if target_bb.insts.inst_exist_by_addr(target_inst_idx)))

                # record the next bb
                src_vertex.branch_type = BasicBlockBranchType.jump
                src_vertex.ordered_succ_bbs.append(dst_vertex.id)

                self.edges.append((src_vertex.id, dst_vertex.id))

            else:

                # Handle IF
                if last_inst.op == Op.IF:
                    target_inst_idx = int(last_inst.result.value)
                    dst_vertex = next((target_bb \
                                       for target_bb in self.blocks.values() \
                                       if target_bb.insts.inst_exist_by_addr(target_inst_idx)))
                    src_vertex.branch_type = BasicBlockBranchType.cond
                    src_vertex.ordered_succ_bbs.append(dst_vertex.id)
                    self.edges.append((src_vertex.id, dst_vertex.id))
                else:
                    src_vertex.branch_type = BasicBlockBranchType.jump

                dst_vertex = next((target_bb \
                                   for target_bb in self.blocks.values() \
                                   if target_bb.insts.inst_exist_by_addr(last_inst_idx + 1)), -1)

                if dst_vertex != -1:
                    src_vertex.ordered_succ_bbs.append(dst_vertex.id)
                    self.edges.append((src_vertex.id, dst_vertex.id))

        for (src, dst) in self.edges:
            self.succ[src].append(dst)
            self.pred[dst].append(src)

        # Add predecessors and successors for all basic blocks.
        # iterate all vertices
        for k, v in self.blocks.items():
            # get all predecessors from self.predecessors[k]
            for n in self.pred[k]:
                v.pred_bbs[n] = self.blocks[n]
            # get all successors from self.successors[k]
            for n in self.succ[k]:
                v.succ_bbs[n] = self.blocks[n]

    def construct_dominator_tree(self):
        for child, parent in self.idom.items():
            child_bb: BasicBlock = self.blocks[child]
            if parent == -1:
                child_bb.dominator_tree_parent = None
                continue

            parent_bb: BasicBlock = self.blocks[parent]
            parent_bb.dominator_tree_children_id.append(child_bb.id)

    def minimal_ssa(self):
        variables: set[str] = set()

        # collect all variables.
        for inst in self.insts.ir_insts:
            if is_assignment_inst(inst):
                variables.add(str(get_assigned_var(inst)))

        # record all blocks which defines variable
        def_sites: Dict[str, List] = {v: [] for v in variables}
        for block in self.blocks.values():
            for inst in block.insts.ret_insts():
                if is_assignment_inst(inst):
                    variable: Variable = get_assigned_var(inst)
                    def_sites[str(variable)].append(block.id)

        # insert phi function for each variable
        for varname in variables:
            # initialize worklist and even_on_worklist

            # the sequence stores blocks that need be handled
            worklist = deque(def_sites[varname])
            even_on_worklist = set(def_sites[varname])

            # handle worklist iteratively
            while worklist:
                # extract current define block id
                def_block_id = worklist.popleft()

                # iterate the dominance frontier of def_block_id
                for y in self.df[def_block_id]:
                    # check if y has phi function of v
                    if not has_phi_for_var(self.blocks[y], varname):
                        # insert phi function as the first inst in y
                        new_phi = create_phi_function(varname, num_pred_s=len(self.pred[y]))
                        self.blocks[y].insts.add_phi_inst(new_phi)

                        # check if y is inserted for the first time, join into worklist.
                        if y not in even_on_worklist:
                            even_on_worklist.add(y)
                            worklist.append(y)

        self.rename_variables(def_sites, variables)

    def rename_variables(self, def_sites: Dict[str, List], variables: set[str]) -> None:

        # initialize version counters
        counters: Dict[str, int] = {v: 0 for v in def_sites.keys()}
        # initialize current version stacks
        stacks = defaultdict(list)
        # record version at the exit of each block { block: { var: version } }
        block_versions: Dict[int, dict] = defaultdict(dict)
        # temporary storage phi operands { block: { var: [operands] }
        phi_operands: Dict[int, dict] = defaultdict(lambda: defaultdict(list))

        for var in variables:
            stacks[var].append(0)

        # We already have built dominator tree.
        # Due to the fact that we set the phi function
        # in the order of dominating the tree for variable
        # renaming, for loop structures (with edges),
        # the versions of variables are not strictly incremented.

        def rename_use_operand(operand: Operand):
            if operand:
                if operand.type == OperandType.VAR:
                    if operand.value.varname in stacks:
                        operand.value.varname = f"{operand.value.varname}-{stacks[operand.value.varname][-1]}"
                elif operand.type == OperandType.ARGS:
                    for arg in operand.value:
                        if arg.type == OperandType.VAR:
                            if arg.value.varname in stacks:
                                arg.value.varname = f"{arg.value.varname}-{stacks[arg.value.varname][-1]}"
            else:
                pass



        # depth first search
        def dfs(block_para: BasicBlock):

            nonlocal counters, stacks, block_versions, phi_operands

            # # record stack status at the entry of the current block.
            # entry_versions = { }
            # for v in variables:
            #     entry_versions[v] = stacks[v][-1]

            # 1
            # handle all phi insts in current block at first
            # allocate new version for phi result.
            phi_def_list: List[str] = [ ]
            for phi_inst_in_cbb in block_para.insts.ret_phi_insts():
                v: Variable = phi_inst_in_cbb.result.value
                # original variable name
                v_n = v.varname.split('-')[0]

                # construct new varname and assign to phi result
                counters[v_n] += 1
                new_ver = counters[v_n]
                new_var = Variable(f"{v_n}-{new_ver}")
                phi_inst_in_cbb.result.value = new_var

                # add new version into stack
                stacks[v_n].append(counters[v_n])
                phi_def_list.append(v_n)


            # 2
            # rename ordinary instructions
            for inst_in_cbb in block_para.insts.ret_ordinary_insts():
                # rename (use) operands
                rename_use_operand(inst_in_cbb.operand1)
                rename_use_operand(inst_in_cbb.operand2)

                # rename (def)
                if is_assignment_inst(inst_in_cbb):
                    v = get_assigned_var(inst_in_cbb)
                    counters[v.varname] += 1
                    new_ver = counters[v.varname]
                    new_var = Variable(f"{v.varname}-{new_ver}")
                    inst_in_cbb.result.value = new_var
                    stacks[v.varname].append(new_ver)

            # 3
            # record variable version at the exit of the current block
            exit_versions = { }
            for v in variables:
                exit_versions[v] = stacks[v][-1]
            block_versions[block_para.id] = exit_versions

            # 4
            # collect operands for phi function in all successors.
            for succ in self.succ[block_para.id]:
                cbb_idx_in_pred = self.pred[succ].index(block_para.id)
                succ_bb = self.blocks[succ]

                if succ not in phi_operands:
                    phi_operands[succ] = { }

                for phi_inst_in_cbb in succ_bb.insts.ret_phi_insts():
                    result: Variable = phi_inst_in_cbb.result.value
                    varname = result.varname.split('-')[0]

                    if varname not in phi_operands[succ]:
                        phi_operands[succ][varname] = [f"{varname}?"] * len(self.pred[succ])

                    current_ver = stacks[varname][-1] if varname in stacks and stacks[varname] else 0
                    # save operands
                    phi_operands[succ][varname][cbb_idx_in_pred] = f"{varname}-{current_ver}"

            # 5
            for child_id in block_para.dominator_tree_children_id:
                dfs(self.blocks[child_id])

            # 6
            # pop up the current scope version when backtracking
            for inst_in_cbb in reversed(block_para.insts.ret_ordinary_insts()):
                if is_assignment_inst(inst_in_cbb):
                    result: Variable = inst_in_cbb.result.value
                    varname = result.varname.split('-')[0]
                    stacks[varname].pop()

            for v in reversed(phi_def_list):
                stacks[v].pop()


        # enter
        dfs(self.root)

        # apply phi operands and rename.
        for block_id, phi_data in phi_operands.items():
            block = self.blocks[block_id]
            for phi in block.insts.ret_phi_insts():
                result_var: Variable = phi.result.value
                base_varname: str = result_var.varname.split('-')[0]

                if base_varname not in phi_data:
                    continue

                operands = [ ]
                for pred_id in self.pred[block_id]:
                    pred_index = self.pred[block_id].index(pred_id)
                    version = phi_data[base_varname][pred_index]
                    operands.append(version)

                phi_args: Args = phi.operand2.value
                for index, operand_str in enumerate(operands):
                    phi_arg_var: Variable = phi_args.args[index].value
                    phi_arg_var.varname = operand_str

    def print_dom_tree(self, block: BasicBlock):
        print(", ".join(map(str, block.dominator_tree_children_id)) + '\t\t\t')
        for child_id in block.dominator_tree_children_id:
            self.print_dom_tree(self.blocks[child_id])

    def __built__(self):
        self.construct_cfg()
        self.dom_comp()
        self.idom_comp()
        self.construct_dominator_tree()
        self.post_order_comp()
        self.dom_front()
        self.df_plus(self.block_id_set)
        # self.print_dom_tree(self.root)
        self.minimal_ssa()

