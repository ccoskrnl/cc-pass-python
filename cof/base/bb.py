from enum import Enum
from typing import List, Optional, Dict
from cof.base.mir import MIRInsts, MIRInst

type BasicBlockId = int

class EdgeType(Enum):
    tree = 0
    forward = 1
    back = 2
    cross = 3

class BasicBlockBranchType(Enum):
    jump = 0
    cond = 1
    switch = 2

class BranchType(Enum):
    FALSE = 0,
    TRUE = 1
    UN_COND = 2,


class BasicBlock:
    def __init__(self, bb_id: Optional[BasicBlockId], insts: Optional[List[MIRInst]]):
    # def __init__(self, bb_id: int, start_idx: int, end_idx: int, insts: MIRInsts):

        # self.inst_idx_list: List[int] = [i for i in range(start_idx, end_idx)]
        # self.insts: List[IRInst] = insts.ir_insts[start_idx: end_idx]
        # self.phi_insts_idx_end = 0
        if insts:
            self.insts: Optional[MIRInsts] = MIRInsts(insts)
            self.first_ordinary_inst: Optional[MIRInst] = insts[0]
            # self.tag: str = "B" + str(bb_id) + "[addr " + str(self.insts.ret_inst_by_idx(-1).addr) + "]"
        else:
            self.insts: Optional[MIRInsts] = None
            self.first_ordinary_inst: Optional[MIRInst] = None
            # self.tag: str = ""


        # self.num_of_insts = (end_idx - start_idx)
        self.id: BasicBlockId = bb_id if isinstance(bb_id, int) else -1

        self.comment: str = ""

        self.branch_type: BasicBlockBranchType = BasicBlockBranchType.jump

        self.preorder: int = -1
        self.rank: int = -1

        # 1. if the branch_type is jump,
        # then the ordered_suc_bbs only has one element, the next bb id.
        # 2. if the branch_type is cond,
        # then the first element of ordered_succ_bbs is true branch target,
        # the second element is false branch target.
        # 3. if the branch_type is switch,
        # then the ordered_succ_bbs has more than two elements.
        self.ordered_succ_bbs: list[int] = []

        self.pred_bbs: Dict[int, 'BasicBlock'] = { }
        self.succ_bbs: Dict[int, 'BasicBlock'] = { }

        self.dominator_tree_parent: Optional['BasicBlock'] = None
        self.dominator_tree_children_id: List[int] = [ ]

    @property
    def tag(self) -> str:
        start_addr = -1
        for inst in self.insts.ret_insts():
            if not inst.is_phi():
                start_addr = inst.addr
                break

        return "B" + str(self.id) + "[addr " + str(start_addr) + "]"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, BasicBlock):
            return False
        return self.id == other.id

    def __str__(self):
        return self.tag

    def add_comment(self, comment: str) -> None:
        self.comment = comment

    # def add_insts(self, start_index, end_index):
    #     self.inst_idx_list.extend([i for i in range(start_index, end_index)])
    #     self.num_of_insts += (end_index - start_index)


