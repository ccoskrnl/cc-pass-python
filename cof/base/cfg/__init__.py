import random
from abc import ABC, abstractmethod
from collections import deque, defaultdict
from typing import Tuple, Optional, Dict, List, Union

from cof.base.bb import BasicBlock, BasicBlockId, BasicBlockBranchType, BranchType
from cof.base.mir import MIRInstId, MIRInst, Args, OperandType, Operand, Op, MIRInsts, Variable, MIRInstAddr
from cof.base.ssa import SSAEdgeBuilder, SSAEdge, SSAVariable, create_phi_function, has_phi_for_var


class ControlFlowGraphABC(ABC):
    """The abstract interface of control flow graph"""
    @abstractmethod
    def entry_block(self) -> BasicBlock:
        pass

    @abstractmethod
    def exit_block(self) -> BasicBlock:
        pass

    @abstractmethod
    def predecessors(self, block_id: BasicBlockId) -> List[BasicBlock]:
        pass

    @abstractmethod
    def successors(self, block_id: BasicBlockId) -> List[BasicBlock]:
        pass

    @abstractmethod
    def block(self, block_id: BasicBlockId) -> BasicBlock:
        pass

    @abstractmethod
    def inst(self, inst_addr: MIRInstAddr) -> MIRInst:
        pass

    @abstractmethod
    def all_blocks(self) -> List[BasicBlock]:
        pass

    def reverse(self) -> 'ControlFlowGraphABC':
        return ReversedCFG(self)

class ControlFlowGraphForDataFlowAnalysis(ControlFlowGraphABC, ABC):
    @abstractmethod
    def collect_definitions(self) -> Dict[Tuple[Variable, MIRInstAddr], BasicBlock]:
        pass

    @abstractmethod
    def collect_use_def(self) -> Tuple[Dict[BasicBlock, set[Variable]], Dict[BasicBlock, set[Variable]]]:
        pass

class ControlFlowGraph(ControlFlowGraphForDataFlowAnalysis):
    def __init__(self, insts: MIRInsts):
        # Instruction List
        self.insts: MIRInsts = insts

        self.insts_dict_by_id: Dict[MIRInstId, MIRInst] = { }
        self.insts_dict_by_addr: Dict[MIRInstAddr, MIRInst] = { }
        self.block_by_inst_id: Dict[MIRInstId, BasicBlock] = { }
        self.block_by_inst_addr: Dict[MIRInstAddr, BasicBlock] = { }

        # The root of the cfg
        self.root: Optional[BasicBlock, None] = None
        self.exit: Optional[BasicBlock, None] = None

        # The number of basic blocks
        self.n_bbs: int = 0
        self.block_id_set: set[BasicBlockId] = set()
        self.block_by_id: Dict[BasicBlockId, BasicBlock] = {}

        # [(src_id, dst_id), (src_Id, dst_id)]
        self.edges: List[Tuple[BasicBlockId, BasicBlockId]] = []
        self.exec_flow: Dict[Tuple[BasicBlockId, BasicBlockId], BranchType] = { }

        # direct predecessor nodes
        self.pred: Dict[BasicBlockId, List[BasicBlockId]] = defaultdict(list)
        # direct successor nodes
        self.succ: Dict[BasicBlockId, List[BasicBlockId]] = defaultdict(list)
        # dominators
        self.dom: Dict[BasicBlockId, set] = {}
        # immediate dominators
        self.idom: Dict[BasicBlockId, BasicBlockId] = {}

        self.post_order: List[BasicBlockId] = []

        # Dominance Frontier
        self.df: Dict[BasicBlockId, set] = {}
        # Dominance Frontier Plus
        self.dfp: set = set()

        self.ranks: Dict[int, int] = {}
        self.max_rank: int = -1

        self._construct_cfg()
        self._assign_ranks()
        self._reassign_inst_id()

    # ++++++++ Initialization ++++++++
    def _construct_cfg(self):

        # The Set type guarantees that there are no identical elements.
        leaders_set_by_addr = set()
        # leaders_set_by_addr.add(0)

        for inst in self.insts.ret_insts():

            self.insts_dict_by_addr[inst.addr] = inst

            match inst.op:
                case Op.ENTRY:
                    leaders_set_by_addr.add(inst.addr)
                    offset = 1
                    for instruction in self.insts.ret_insts()[1:]:
                        if instruction.is_init():
                            offset += 1
                        else:
                            break
                    leaders_set_by_addr.add(inst.addr + offset)
                case Op.EXIT:
                    leaders_set_by_addr.add(inst.addr)

                case Op.IF:
                    leaders_set_by_addr.add(inst.addr + 1)
                    assert inst.result.type == OperandType.PTR
                    target = int(inst.result.value)
                    leaders_set_by_addr.add(target)

                case Op.GOTO:
                    assert inst.result.type == OperandType.PTR
                    target = int(inst.result.value)
                    leaders_set_by_addr.add(target)


        # Constructing Basic Blocks and updating class members
        sorted_list = sorted(leaders_set_by_addr)
        for leader_idx in range(0, len(sorted_list) - 1):
            block_insts: List[MIRInst] = []
            for i in range(sorted_list[leader_idx], sorted_list[leader_idx+1]):
                found_inst = self.insts.find_inst_by_key(key="addr", value=i)
                if found_inst:
                    block_insts.append(found_inst)

            self.new_a_block(self.n_bbs, block_insts)

        # Construct the exit basic block
        block_insts: List[MIRInst] = []
        for i in range(sorted_list[-1], self.insts.num):
            found_inst = self.insts.find_inst_by_key(key="addr", value=i)
            if found_inst:
                block_insts.append(found_inst)
        self.exit = self.new_a_block(self.n_bbs, block_insts)

        self.root = self.block_by_id[0]

        # Updating Edges in the CFG
        for src_vertex in self.block_by_id.values():

            # Get the last inst in basic block.
            last_inst = src_vertex.insts.ret_inst_by_idx(-1)
            last_inst_idx = last_inst.addr

            # Handling GOTO statement
            if last_inst.op == Op.GOTO:
                target_inst_idx = int(last_inst.result.value)
                dst_vertex = None
                for target_bb in self.block_by_id.values():
                    if target_bb.insts.inst_exist_by_key(key="addr", value=target_inst_idx):
                        dst_vertex = target_bb
                        break
                # dst_vertex = next((target_bb \
                #                for target_bb in self.blocks.values() \
                #                if target_bb.insts.inst_exist_by_key(key="addr", value=target_inst_idx)))
                #                     # if target_bb.insts.inst_exist_by_addr(target_inst_idx)))

                # record the next bb
                src_vertex.branch_type = BasicBlockBranchType.jump
                src_vertex.ordered_succ_bbs.append(dst_vertex.id)

                self.edges.append((src_vertex.id, dst_vertex.id))
                self.exec_flow[(src_vertex.id, dst_vertex.id)] = BranchType.UN_COND

            else:

                # Handle IF
                if last_inst.op == Op.IF:
                    target_inst_idx = int(last_inst.result.value)
                    dst_vertex = next((target_bb \
                                       for target_bb in self.block_by_id.values() \
                                       if target_bb.insts.inst_exist_by_key(key="addr", value=target_inst_idx)))
                                        # if target_bb.insts.inst_exist_by_addr(target_inst_idx)))

                    src_vertex.branch_type = BasicBlockBranchType.cond
                    src_vertex.ordered_succ_bbs.append(dst_vertex.id)
                    self.edges.append((src_vertex.id, dst_vertex.id))
                    self.exec_flow[(src_vertex.id, dst_vertex.id)] = BranchType.TRUE
                else:
                    src_vertex.branch_type = BasicBlockBranchType.jump

                dst_vertex = next((target_bb \
                                   for target_bb in self.block_by_id.values() \
                                   if target_bb.insts.inst_exist(lambda ins: ins.addr == (last_inst_idx + 1))), -1)

                if dst_vertex != -1:
                    src_vertex.ordered_succ_bbs.append(dst_vertex.id)
                    self.edges.append((src_vertex.id, dst_vertex.id))
                    if last_inst.op == Op.IF:
                        self.exec_flow[(src_vertex.id, dst_vertex.id)] = BranchType.FALSE
                    else:
                        self.exec_flow[(src_vertex.id, dst_vertex.id)] = BranchType.UN_COND


        for (src_id, dst_id) in self.edges:
            self.succ[src_id].append(dst_id)
            self.pred[dst_id].append(src_id)

        # Add predecessors and successors for all basic blocks.
        # iterate all vertices
        for k, v in self.block_by_id.items():
            # get all predecessors from self.predecessors[k]
            for n in self.pred[k]:
                v.pred_bbs[n] = self.block_by_id[n]
            # get all successors from self.successors[k]
            for n in self.succ[k]:
                v.succ_bbs[n] = self.block_by_id[n]

    def _assign_ranks(self):
        """
        Depth First Search to assign rank for every block.
        :return:
        """

        # initialize
        for block in self.block_by_id.values():
            self.ranks[block.id] = -1

        preorder = 0

        # Preorder traversal
        queue = deque([self.root])
        self.ranks[self.root.id] = 0
        # self.block_preorder[0].append(self.root)
        self.root.rank = 0
        self.root.preorder = preorder

        while queue:

            # FIFO
            current_vbb = queue.popleft()
            current_rank = self.ranks[current_vbb.id]

            match current_vbb.branch_type:
                case BasicBlockBranchType.jump:

                    if not current_vbb.ordered_succ_bbs:
                        continue

                    next_vbb = self.block_by_id[current_vbb.ordered_succ_bbs[0]]
                    next_rank = current_rank + 1
                    if self.ranks[next_vbb.id] < 0 or self.ranks[next_vbb.id] > next_rank:
                        preorder += 1
                        next_vbb.rank = next_rank
                        next_vbb.preorder = preorder

                        self.ranks[next_vbb.id] = next_rank
                        # add the visual basic block into block_order dict
                        # self.block_preorder[next_rank].append(next_vbb)
                        queue.append(next_vbb)

                case BasicBlockBranchType.cond:
                    true_br_vbb = self.block_by_id[current_vbb.ordered_succ_bbs[0]]
                    false_br_vbb = self.block_by_id[current_vbb.ordered_succ_bbs[1]]
                    next_rank = current_rank + 1

                    # guarantee the first element of block order is false condition branch target vbb
                    if self.ranks[false_br_vbb.id] < 0 or self.ranks[false_br_vbb.id] > next_rank:
                        preorder += 1
                        false_br_vbb.rank = next_rank
                        false_br_vbb.preorder = preorder

                        self.ranks[false_br_vbb.id] = next_rank
                        # self.block_preorder[next_rank].append(false_br_vbb)
                        queue.append(false_br_vbb)

                    if self.ranks[true_br_vbb.id] < 0 or self.ranks[true_br_vbb.id] > next_rank:
                        preorder += 1
                        true_br_vbb.rank = next_rank
                        true_br_vbb.preorder = preorder

                        self.ranks[true_br_vbb.id] = next_rank
                        # self.block_preorder[next_rank].append(true_br_vbb)
                        queue.append(true_br_vbb)

                case BasicBlockBranchType.switch:
                    next_rank = current_rank + 1
                    for vbb_id in current_vbb.ordered_succ_bbs:
                        next_vbb = self.block_by_id[vbb_id]
                        if self.ranks[next_vbb.id] < 0 or self.ranks[next_vbb.id] > next_rank:
                            preorder += 1
                            next_vbb.rank = next_rank
                            next_vbb.preorder = preorder

                            self.ranks[next_vbb.id] = next_rank
                            # self.block_preorder[next_rank].append(next_vbb)
                            queue.append(next_vbb)

        # self.handle_loops()
        self.max_rank = max(self.ranks.values())


    # ++++++++ ABC ++++++++
    def entry_block(self) -> BasicBlock:
        return self.root

    def exit_block(self) -> BasicBlock:
        return self.exit

    def predecessors(self, block_id: BasicBlockId) -> List[BasicBlock]:
        pred_bb_list: List[BasicBlock] = [self.block(p) for p in self.pred[block_id]]
        return pred_bb_list

    def successors(self, block_id: BasicBlockId) -> List[BasicBlock]:
        succ_bb_list: List[BasicBlock] = [self.block(p) for p in self.succ[block_id]]
        return succ_bb_list

    def block(self, block_id: BasicBlockId) -> BasicBlock:
        return self.block_by_id[block_id]

    def inst(self, inst_addr: MIRInstAddr) -> MIRInst:
        return self.insts_dict_by_addr[inst_addr]

    def all_blocks(self) -> List[BasicBlock]:
        return list(self.block_by_id.values())



    # ++++++++ Dominator ++++++++
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

                dominator_set = {n} | tmp_dominator_set
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
            tmp[n] = self.dom[n] - {n}
            new_tmp[n] = self.dom[n] - {n}

        for n in self.block_id_set - {root_id}:
            for s in tmp[n]:
                for t in tmp[n] - {s}:
                    if t in tmp[s]:
                        new_tmp[n] -= {t}

        for n in self.block_id_set - {root_id}:
            self.idom[n] = random.choice(list(new_tmp[n]))

    def construct_dominator_tree(self):
        for child, parent in self.idom.items():
            child_bb: BasicBlock = self.block_by_id[child]
            if parent == -1:
                child_bb.dominator_tree_parent = None
                continue

            parent_bb: BasicBlock = self.block_by_id[parent]
            parent_bb.dominator_tree_children_id.append(child_bb.id)

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


    # ++++++++ Data-Flow Analysis ++++++++
    def collect_definitions(self) -> Dict[Tuple[Variable, MIRInstAddr], BasicBlock]:
        def_dict = { }
        for inst in self.insts.ret_ordinary_insts():

            block = self.block_by_inst_addr.get(inst.addr, None)
            if not block:
                continue

            if inst.is_assignment():
                def_dict[(inst.get_dest_var().value, inst.addr)] = block

        return def_dict

    def collect_use_def(self) -> Tuple[Dict[BasicBlock, set[Variable]], Dict[BasicBlock, set[Variable]]]:
        def_dict: Dict[BasicBlock, set[Variable]] = defaultdict(set)

        # undefined before use.
        use_dict: Dict[BasicBlock, set[Variable]] = defaultdict(set)

        # local definitions
        # local_def_tracker = defaultdict(set)

        block_defs = defaultdict(set)

        for block in self.all_blocks():
            for inst in block.insts.ret_ordinary_insts():
                if inst.is_assignment():
                    var = inst.get_dest_var().value
                    def_dict[block].add(var)
                    block_defs[block].add(var)

        for block in self.all_blocks():
            local_defs = set()
            for inst in block.insts.ret_ordinary_insts():

                for operand in inst.get_operand_list():
                    var = operand.value
                    if isinstance(var, Variable):
                        if var not in local_defs and var not in block_defs[block]:
                            use_dict[block].add(var)

                if inst.is_assignment():
                    var = inst.get_dest_var().value
                    local_defs.add(var)

                # TODO: Special handling: Function calls may implicitly
                #       use global variables

                # if inst.is_call() and inst.modifies_global_state():
                #     for global_var in self.get_global_variables():
                #         if global_var not in local_defs:
                #             use_dict[block].add(global_var)

        return use_dict, def_dict

    # ++++++++ SSA ++++++++
    def _dom_front(self):
        """
        Dominance Frontier
        :return:
        """
        df: Dict[int, set] = {i: set() for i in range(self.n_bbs)}

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

    def _df_plus(self, sn):
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

    def _rename_variables(self, def_sites: Dict[str, List], variables: set[str]) -> None:

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
        # in the order of visiting dominator tree for variable
        # renaming, for loop structures (with back edges),
        # the versions of variables are not strictly incremented.

        def rename_use_operand(operand: Operand):
            if operand:
                if operand.type == OperandType.VAR:
                    if operand.value.varname in stacks:
                        operand.type = OperandType.SSA_VAR
                        operand.value = SSAVariable(operand.value, stacks[operand.value.varname][-1])

                elif operand.type == OperandType.ARGS:
                    for arg in operand.value.args:
                        # if arg.type == OperandType.VAR:
                        if isinstance(arg.value, Variable):
                            if arg.value.varname in stacks:
                                arg.type = OperandType.SSA_VAR
                                arg.value = SSAVariable(arg.value, stacks[arg.value.varname][-1])


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
            phi_def_list: List[str] = []
            for phi_inst_in_cbb in block_para.insts.ret_phi_insts():
                assert isinstance(phi_inst_in_cbb.result.value, SSAVariable)
                v: SSAVariable = phi_inst_in_cbb.result.value
                # original variable name
                v_n = v.base_name

                # construct new varname and assign to phi result
                counters[v_n] += 1
                v.version = counters[v_n]

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
                if inst_in_cbb.is_assignment():
                    v: Variable = inst_in_cbb.get_dest_var().value
                    counters[v.varname] += 1
                    new_ver = counters[v.varname]
                    new_var = SSAVariable(v, new_ver)

                    inst_in_cbb.result.type = OperandType.SSA_VAR
                    inst_in_cbb.result.value = new_var

                    stacks[v.varname].append(new_ver)

            # 3
            # record variable version at the exit of the current block
            exit_versions = {}
            for v in variables:
                exit_versions[v] = stacks[v][-1]
            block_versions[block_para.id] = exit_versions

            # 4
            # collect operands for phi function in all successors.
            for succ in self.succ[block_para.id]:
                cbb_idx_in_pred = self.pred[succ].index(block_para.id)
                succ_bb = self.block_by_id[succ]

                if succ not in phi_operands:
                    phi_operands[succ] = {}

                for phi_inst_in_cbb in succ_bb.insts.ret_phi_insts():
                    result: SSAVariable = phi_inst_in_cbb.result.value
                    varname = result.base_name

                    if varname not in phi_operands[succ]:
                        phi_operands[succ][varname] = [-1] * len(self.pred[succ])  # default version

                    current_ver = stacks[varname][-1] if varname in stacks and stacks[varname] else 0
                    # save operands
                    phi_operands[succ][varname][cbb_idx_in_pred] = current_ver

            # 5
            for child_id in block_para.dominator_tree_children_id:
                dfs(self.block_by_id[child_id])

            # 6
            # pop up the current scope version when backtracking
            for inst_in_cbb in reversed(block_para.insts.ret_ordinary_insts()):
                if inst_in_cbb.is_assignment():
                    if isinstance(inst_in_cbb.result.value, Variable):
                        result: Variable = inst_in_cbb.result.value
                        varname = result.varname
                        stacks[varname].pop()
                    elif isinstance(inst_in_cbb.result.value, SSAVariable):
                        result: SSAVariable = inst_in_cbb.result.value
                        stacks[result.base_name].pop()
                    else:
                        raise TypeError("Only Variables or SSAVariables are allowed")

            for v in reversed(phi_def_list):
                stacks[v].pop()

        # enter
        dfs(self.root)

        # apply phi operands and rename.
        for block_id, phi_data in phi_operands.items():

            # calculate pred block index
            pred_index_map: Dict[int, int] = {pred_id: idx for idx, pred_id in enumerate(self.pred[block_id])}

            block: BasicBlock = self.block_by_id[block_id]

            for phi in block.insts.ret_phi_insts():
                result_var: SSAVariable = phi.result.value
                base_varname: str = result_var.base_name

                if base_varname not in phi_data:
                    continue

                phi_args: Args = phi.operand2.value
                for index, pred_id in enumerate(self.pred[block_id]):
                    # get index from dict
                    pred_index = pred_index_map[pred_id]
                    # obtain the version number of the corresponding predecessor.
                    version = phi_data[base_varname][pred_index]
                    phi_arg_var: SSAVariable = phi_args.args[index].value
                    phi_arg_var.version = version

    def minimal_ssa(self):
        self._dom_front()
        self._df_plus(self.block_id_set)

        variables: set[str] = set()

        # collect all variables.
        for inst in self.insts.ir_insts:
            if inst.is_assignment():
                variables.add(str(inst.get_dest_var().value))

        # record all blocks which defines variable
        def_sites: Dict[str, List] = {v: [] for v in variables}
        for block in self.block_by_id.values():
            for inst in block.insts.ret_insts():
                if inst.is_assignment():
                    variable: Variable = inst.get_dest_var().value
                    def_sites[str(variable)].append(block.id)

        # insert phi function for each variable
        for varname in variables:
            # initialize worklist and even_on_worklist

            # the sequence stores blocks that need be handled
            worklist = deque(def_sites[varname])
            even_on_worklist = set(def_sites[varname])

            # if the variable only be defined once, then we're done.
            if len(even_on_worklist) == 1:
                continue

            # handle worklist iteratively
            while worklist:
                # extract current define block id
                def_block_id = worklist.popleft()

                # iterate the dominance frontier of def_block_id
                for y in self.df[def_block_id]:
                    y_block = self.block_by_id[y]
                    # check if y has phi function of v
                    if not has_phi_for_var(y_block, varname):

                        # insert phi function as the first inst in y
                        new_phi = create_phi_function(varname, num_pred_s=len(self.pred[y]))
                        insert_index = self.insts.index_for_inst(y_block.first_ordinary_inst)
                        # add phi inst into cfg insts
                        self.add_new_inst(insert_index, new_phi)
                        # add phi inst into block insts
                        y_block.insts.add_phi_inst(new_phi)

                        # check if y is inserted for the first time, join into worklist.
                        if y not in even_on_worklist:
                            even_on_worklist.add(y)
                            worklist.append(y)

        self._rename_variables(def_sites, variables)

        # After we have inserted phi function, we need to reassign inst id.
        self._reassign_inst_id()

    def ssa_edges_comp(self, loop_info) -> 'SSAEdgeBuilder':
        """
        Note:
            Must be guaranteed that all variables have been converted to SSAVariable form before
            calling this routine.
        :return:
        """
        edges: List[SSAEdge] = []
        def_sites: Dict[str, int] = {}  # var_name -> MIRInst.id
        phi_sources = defaultdict(list)  # phi_inst_id -> original definition list

        def is_loop_carried(phi_block: BasicBlock, def_block: BasicBlock, lo) -> bool:
            """
            check if edge which from definition inst to phi inst is loop carried
            :param phi_block:
            :param def_block:
            :param lo: Loop Info
            :return:
            """

            phi_loop = lo.get_loop_for_block(phi_block)

            if not phi_loop:
                return False

            # check if definition block is in the same loop.
            if phi_loop.contains_block(def_block):
                # check if definition block is in the loop body (not header)
                if def_block != phi_loop.header:
                    return True

            return False

        # stage 1.
        # collect all definition.
        for block in self.block_by_id.values():
            for inst in block.insts.ret_ordinary_insts():
                if inst.is_assignment():
                    var: SSAVariable = inst.result.value
                    def_sites[str(var)] = inst.id

            for phi_inst in block.insts.ret_phi_insts():
                var: SSAVariable = phi_inst.result.value
                def_sites[str(var)] = phi_inst.id
                phi_sources[phi_inst.id] = []

        # stage 2.
        # connect common use.
        for block in self.block_by_id.values():
            for inst in block.insts.ret_ordinary_insts():
                operand_list = inst.get_operand_list()
                for operand in operand_list:
                    if isinstance(operand.value, SSAVariable) and str(operand.value) in def_sites:
                        src_inst_id = def_sites[str(operand.value)]
                        edges.append(SSAEdge(
                            self.insts_dict_by_id[src_inst_id]
                            , inst
                            , self.find_defining_block(src_inst_id)
                            , block
                            , str(operand.value)))

        # stage 3.
        # handle phi instructions.
        for block in self.block_by_id.values():
            for phi in block.insts.ret_phi_insts():

                # get predecessor id list
                predecessor_id_list = self.pred[block.id]

                for i, operand in enumerate(phi.get_operand_list()):
                    assert isinstance(operand.value, SSAVariable)
                    ssa_name = str(operand.value)
                    if ssa_name in def_sites:
                        src_inst_id = def_sites[ssa_name]
                        # find block which has defined the var.
                        src_block = self.find_defining_block(src_inst_id)

                        if src_block and src_block.id in predecessor_id_list:

                            ssa_edge = SSAEdge(
                                self.insts_dict_by_id[src_inst_id]
                                , phi
                                , self.find_defining_block(src_inst_id)
                                , block
                                , ssa_name)

                            if is_loop_carried(block, src_block, loop_info):
                                ssa_edge.mark_loop_carried()
                            edges.append(ssa_edge)

        return SSAEdgeBuilder(self, edges, def_sites)


    # ++++++++ Management ++++++++
    def _reassign_inst_id(self):
        for i, inst in enumerate(self.insts.ret_insts()):
            inst.id = i

        self.insts_dict_by_id = {inst.id: inst for inst in self.insts.ret_insts()}

        for block in self.block_by_id.values():
            for inst in block.insts.ret_insts():
                self.block_by_inst_id[inst.id] = block
                if not inst.is_phi():
                    self.block_by_inst_addr[inst.addr] = block



    def new_a_block(self, bb_id: BasicBlockId, block_insts: List[MIRInst]) -> BasicBlock:
        src_vertex = BasicBlock(bb_id, block_insts)

        self.block_by_id[bb_id] = src_vertex
        self.block_id_set.add(bb_id)
        self.n_bbs += 1

        return src_vertex

    def find_defining_block(self, inst: Union[MIRInstId, MIRInst]) -> Optional[BasicBlock]:
        if isinstance(inst, int):
            return self.block_by_inst_id[inst]
        elif isinstance(inst, MIRInst):
            return self.block_by_inst_id[inst.id]
        return None

    def add_new_inst(self, index: int, inst: MIRInst):
        """
        Add new inst to insts.
        TODO:
            handle self.insts_dict_by_id, self.insts_dict_by_addr.
            add the inst to the corresponding basic block.

        """
        self.insts.insert_insts(index, inst)

    def print_dom_tree(self, block: BasicBlock):
        print(", ".join(map(str, block.dominator_tree_children_id)) + '\t\t\t')
        for child_id in block.dominator_tree_children_id:
            self.print_dom_tree(self.block_by_id[child_id])

    def initialize(self):
        self.dom_comp()
        self.idom_comp()
        self.construct_dominator_tree()
        self.post_order_comp()

        self._dom_front()
        self._df_plus(self.block_id_set)


class ReversedCFG(ControlFlowGraphABC):
    def __init__(self, original: ControlFlowGraphABC):
        self.original = original

    def entry_block(self) -> BasicBlock:
        return self.original.exit_block()

    def exit_block(self) -> BasicBlock:
        return self.original.entry_block()

    def predecessors(self, block_id: BasicBlockId) -> List[BasicBlock]:
        return self.original.successors(block_id)

    def successors(self, block_id: BasicBlockId) -> List[BasicBlock]:
        return self.original.predecessors(block_id)

    def all_blocks(self) -> List[BasicBlock]:
        return self.original.all_blocks()

    def block(self, block_id: BasicBlockId) -> BasicBlock:
        return self.original.block(block_id)

    def inst(self, inst_addr: MIRInstAddr) -> MIRInst:
        return self.inst(inst_addr)

class FlattenBasicBlocks:
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg: ControlFlowGraph = cfg
        self.succ: Dict[MIRInstId, List[MIRInstId]] = defaultdict(list)
        self.edges: List[Tuple[MIRInstId, MIRInstId]] = [ ]
        self.exec_flow: Dict[Tuple[MIRInstId, MIRInstId], bool] = { }


    def flatten_blocks(self):

        visited: Dict[int, bool] = {b.id: False for b in self.cfg.block_by_id.values()}

        def handle_block(block: BasicBlock):

            if visited[block.id]:
                return
            else:
                visited[block.id] = True

            # get all instructions
            insts = block.insts.ret_insts()

            # handle the current block
            for idx, inst in enumerate(insts[:-1]):
                idx += 1
                self.succ[inst.id].append(insts[idx].id)
                edge = (inst.id, insts[idx].id)
                self.edges.append(edge)

            # handle the successors of the block
            last_inst = insts[-1]
            for b_id in self.cfg.succ[block.id]:
                find_false_branch = False
                succ_block = self.cfg.block_by_id[b_id]

                # the false branch address is the address of the current instruction plus one.
                next_inst_of_false_branch = succ_block.insts.find_inst_by_key(key="addr", value=last_inst.addr + 1)
                if next_inst_of_false_branch:
                    find_false_branch = True

                next_inst_of_true_branch = succ_block.insts.ret_inst_by_idx(0)
                self.succ[last_inst.id].append(next_inst_of_true_branch.id)

                edge = (last_inst.id, next_inst_of_true_branch.id)
                self.edges.append(edge)

                if last_inst.is_if():
                    self.exec_flow[edge] = False if find_false_branch else True

                handle_block(succ_block)

        handle_block(self.cfg.root)
