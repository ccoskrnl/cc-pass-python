import bisect
from collections import deque
from typing import Dict, Set

from cof.base.cfg import ControlFlowGraph
from .vbb import VisualBasicBlock

TITLE_GAP = 5
CONTENT_GAP = 1
BLOCK_PAINT_WIDTH_PAD = 30

class Tree:
    def __init__(self, vbb: VisualBasicBlock, width: int, height: int):
        self.vbb: VisualBasicBlock = vbb
        self.vbb.tree = self

        self.width = width
        self.height = height

        self.children: list[Tree] = []
        self.num_of_children = 0
        self.parent = None

        # 最终水平位置
        self.x = 0
        # 最终垂直位置
        self.y = 0
        # 初步x坐标（相对于父节点）
        self.prelim = 0
        # 计算的修饰符(用于调整位置)
        self.modifier = 0
        # 整体位移值
        self.shift = 0
        # 位置变化量
        self.change = 0

        # 轮廓线处理相关成员
        """
        1. 左轮廓，从根节点开始，沿着每层最左侧节点向下延伸的路径，形成树的左边界
        2. 右轮廓，从根节点开始，沿着每层最右侧节点向下延伸的路径，形成树的右边界
        """
        self.left_contour_thread = None  # 左轮廓线程
        self.right_contour_thread = None  # 右轮廓线程
        self.extreme_left_tree = None  # 极左节点，最左侧后代节点
        self.extreme_right_tree = None  # 极右节点，最右侧后代节点
        # 极端节点的修饰符总和
        self.modifier_summation_of_extreme_left_tree = 0   # 最左侧节点的修饰符累计值
        self.modifier_summation_of_extreme_right_tree = 0   # 最右侧节点的修饰符累计值

    def add_child(self, new_child):
        """添加子节点"""
        new_child.parent = self
        preorders = [child.vbb.preorder for child in self.children]
        idx = bisect.bisect_left(preorders, new_child.vbb.preorder)
        self.children.insert(idx, new_child)
        self.num_of_children += 1

    def is_leaf(self):
        return True if self.num_of_children == 0 else False

    def set_extremes(self):
        """设置树的极节点"""
        if self.is_leaf():
            self.extreme_left_tree = self
            self.extreme_right_tree = self

            self.modifier_summation_of_extreme_left_tree = self.modifier_summation_of_extreme_right_tree = 0
        else:
            # 非叶子节点：
            # 继承第一个子节点的最左节点
            self.extreme_left_tree = self.children[0].extreme_left_tree
            self.modifier_summation_of_extreme_left_tree = self.extreme_left_tree.modifier_summation_of_extreme_left_tree
            # 继承第一个子节点的最右节点
            self.extreme_right_tree = self.children[-1].extreme_right_tree
            self.modifier_summation_of_extreme_right_tree = self.extreme_right_tree.modifier_summation_of_extreme_right_tree

    def bottom(self) -> int:
        return self.y + self.height

    def next_left_contour(self):
        """
        返回树的下一个左轮廓节点
        :return:
        """
        return self.left_contour_thread if self.num_of_children == 0 else self.children[0]

    def next_right_contour(self):
        """
        返回树的下一个右轮廓节点
        :return:
        """
        return self.right_contour_thread if self.num_of_children == 0 else self.children[-1]

    def set_left_thread(self, i, cl, modsumcl):
        """
        处理轮廓线断裂的情况
        :param i: 当前子节点的索引（需要设置线程的子节点）
        :param cl: 当前子树左轮廓的节点（需要连接的节点）
        :param modsumcl: 从父节点到cl节点路径上所有修饰符的累计加
        :return:
        """

        # 获取父节点第一个子节点的最左节点，这是需要连接线程的起始点
        li: Tree = self.children[0].extreme_left_tree

        # 设置左线程指向当前子树左轮廓节点，建立轮廓线的连续性
        li.left_contour_thread = cl

        # 计算修饰符差值
        # 确保线程两端的修饰符累加值一致，保持位置计算的准确性
        diff = (modsumcl - cl.modifier) - self.children[0].modifier_summation_of_extreme_right_tree

        li.modifier += diff
        li.prelim -= diff

        # 将父节点的极左节点更新为当前子树的极左节点
        self.children[0].extreme_left_tree = self.children[i].extreme_left_tree
        self.children[0].modifier_summation_of_extreme_left_tree = self.children[i].modifier_summation_of_extreme_left_tree

    def set_right_thread(self, i, sr, modsumsr):

        ri: Tree = self.children[i].extreme_left_tree
        ri.right_contour_thread = sr

        diff = modsumsr - sr.modifier - self.children[i].modifier_summation_of_extreme_right_tree
        ri.modifier += diff
        ri.prelim -= diff

        self.children[i].extreme_right_tree = self.children[i - 1].extreme_right_tree
        self.children[i].modifier_summation_of_extreme_right_tree = self.children[i - 1].modifier_summation_of_extreme_right_tree

    def position_root(self):
        self.prelim = (self.children[0].prelim + self.children[0].modifier
                        + self.children[-1].prelim + self.children[-1].modifier
                        + self.children[-1].width) / 2 - self.width / 2

class IYL:
    """Indexed Y List"""
    def __init__(self, low_y, index, next_node):
        # 当前子树的最低Y坐标
        self.lowY = low_y

        # 子节点索引
        self.index = index

        # 下一个IYL节点
        self.next = next_node

def update_IYL(min_y, i, ih=None) -> IYL:
    """当添加新子树时，移除所有被新子树完全遮挡的左侧兄弟"""
    while ih and min_y >= ih.lowY:
        ih = ih.next

    # 添加新子树
    return IYL(min_y, i, ih)

def separate(tree: Tree, i: int, ih: IYL) -> None:
    """通过比较左右轮廓线，计算子树间所需间距"""
    # 当前子树的左兄弟的右轮廓
    sr: Tree = tree.children[i - 1]
    # 右轮廓的修饰值合
    mssr = sr.modifier
    # 当前子树的左轮廓
    cl: Tree = tree.children[i]
    # 左轮廓的修饰值合
    mscl = cl.modifier

    # 如果右轮廓和左轮廓都不为None，我们需要调整间距，保证子树之间不重叠
    while sr and cl:
        # 计算重叠距离（需要分离的距离）
        distance = mssr \
                   + sr.prelim \
                   + sr.width \
                   - (mscl
                      + cl.prelim)

        if distance > 0:
            mscl += distance
            move_subtree(tree, i, ih.index, distance)

        # 选择较低侧的轮廓线继续比较
        if sr.bottom() <= cl.bottom():
            sr = sr.next_right_contour()
            if sr:
                mssr += sr.modifier

        elif sr.bottom() >= cl.bottom():
            cl = cl.next_left_contour()
            if cl:
                mscl += cl.modifier

    # 当左兄弟子树的右轮廓结束，而当前子树的左轮廓还有剩余时
    if not sr and cl:
        tree.set_left_thread(i, cl, mscl)
    # 当当前子树的左轮廓结束，而左侧兄弟子树的右轮廓还有剩余时
    elif sr and not cl:
        tree.set_right_thread(i, sr, mssr)

def move_subtree(tree: Tree, index: int, start_index: int, distance: int) -> None:
    """
    调整子树位置并分配空间
    :param tree: 父树
    :param index: 需要移动的子树在父树的子树列表中索引
    :param start_index: 子树列表的起始索引（指需要移动的子树集）
    :param distance: 移动的距离
    :return:
    """

    tree.children[index].modifier += distance
    tree.children[index].modifier_summation_of_extreme_left_tree += distance
    tree.children[index].modifier_summation_of_extreme_right_tree += distance
    distribute_extra(tree, index, start_index, distance)

def distribute_extra(tree: Tree, index: int, start_index: int, distance: int) -> None:
    """
    将移动量分摊到中间子树，避免空隙过大
    :param tree: 父树
    :param index: 需要移动的子树在父树的子树列表中索引
    :param start_index: 子树列表的起始索引（指需要移动的子树集）
    :param distance: 移动的距离
    :return:
    """

    if start_index != index - 1:
        num_of_subtrees = index - start_index
        tree.children[start_index + 1].shift += distance / num_of_subtrees
        tree.children[index].shift -= distance / num_of_subtrees
        tree.children[index].change -= distance - distance / num_of_subtrees

def add_child_spacing(tree: Tree):
    d = 0
    modsum_delta = 0

    for i in range(0, tree.num_of_children):
        d += tree.children[i].shift
        modsum_delta += d + tree.children[i].change
        tree.children[i].modifier += modsum_delta

def first_walk(tree: Tree):

    if tree.parent:
        tree.y = tree.parent.y + tree.parent.height

    if tree.num_of_children == 0:
        tree.set_extremes()
        return

    # 递归处理第一个子节点
    first_walk(tree.children[0])

    ih = update_IYL(tree.children[0].extreme_left_tree.bottom(), 0)

    for i in range(1, tree.num_of_children):
        first_walk(tree.children[i])

        min_y = tree.children[i].extreme_right_tree.bottom()

        separate(tree, i, ih)

        ih = update_IYL(min_y, i, ih)

    tree.position_root()
    tree.set_extremes()

def second_walk(tree: Tree, modsum):
    modsum += tree.modifier

    # 计算绝对位置
    tree.x = tree.prelim + modsum

    add_child_spacing(tree)
    for i in range(0, tree.num_of_children):
        second_walk(tree.children[i], modsum)

class TreeLayout:
    def __init__(self, root: Tree):
        self.root: Tree = root

    def layout(self):
        first_walk(self.root)
        second_walk(self.root, 0)


class CFGLayout:
    def __init__(self, cfg: ControlFlowGraph, entry_block: VisualBasicBlock, blocks: Dict):
        self.block_color = None
        self.title_font = None
        self.title_font_color = None
        self.title_font_matrics = None
        self.content_font = None
        self.content_font_color = None
        self.content_font_matrics = None

        self.entry_block: VisualBasicBlock = entry_block
        self.blocks: Dict[int, VisualBasicBlock] = blocks

        self.max_rank = cfg.max_rank
        self.ranks: Dict[int, int] = cfg.ranks

        self.tree_layout = None
        self.root = None

        # a dict, key is rank, value is a list[VisualBasicBlock]
        # self.block_preorder = defaultdict(list)
        # self.positions: Dict = { }

    def calculate_block_size(self, block: VisualBasicBlock):
        block.color = self.block_color
        block.title_font = self.title_font
        block.title_font_color = self.title_font_color
        block.title_font_matrics = self.title_font_matrics
        block.content_font = self.content_font
        block.content_font_color = self.content_font_color
        block.content_font_matrics = self.content_font_matrics

        max_width = 0
        # find the least width for longest inst
        for inst in block.content.split('\n'):
            line_width = block.content_font_matrics.horizontalAdvance(inst)
            if line_width > max_width:
                max_width = line_width

        # compare the least width with title
        title_width = block.title_font_matrics.horizontalAdvance(block.title)
        if title_width > max_width:
            max_width = title_width

        block.title_height = block.title_font_matrics.height() + TITLE_GAP
        block.content_body_height = block.content_font_matrics.height() * (len(block.insts.ret_insts()) + CONTENT_GAP)
        block.height = block.title_height + block.content_body_height
        block.width = max_width + BLOCK_PAINT_WIDTH_PAD
        block.padded_height = block.height + block.height_pad * 2
        block.padded_width = block.width + block.width_pad * 2

    def handle_loops(self):
        """Handle loop structure layer"""

        back_edges = []
        for block in self.blocks.values():
            for succ in block.succ_bbs.values():
                if self.ranks[succ.id] < self.ranks[block.id]:
                    back_edges.append((block, succ))

        for back_edge in back_edges:
            # The loop header
            header = back_edge[1]

            # The loop tail
            loop_tail = back_edge[0]
            loop_blocks = self.find_loop_blocks(header, loop_tail)

            min_rank = min(self.ranks[b.id] for b in loop_blocks)
            for block in loop_blocks:
                self.ranks[block.id] = min_rank

    def find_loop_blocks(self, header, back_edge_source) -> Set:
        """Find all blocks be contained in loop"""
        loop_blocks = {header, back_edge_source}
        queue = deque([back_edge_source])

        while queue:
            current = queue.popleft()
            for pred in current.pred_bbs.values():
                if pred not in loop_blocks and self.ranks[pred.id] >= self.ranks[header.id]:
                    loop_blocks.add(pred)
                    queue.append(pred)

        return loop_blocks

    def initialize_cfg_layout(self):
        for block in self.blocks.values():
            self.calculate_block_size(block)

        # self.assign_ranks()

    def layout(self):
        root = Tree(self.entry_block, self.entry_block.padded_width, self.entry_block.padded_height)
        queue = deque([root])
        while queue:
            current_node = queue.popleft()

            for succ_vbb in current_node.vbb.succ_vbbs:
                if current_node.vbb.rank < succ_vbb.rank:
                    if succ_vbb.tree:
                        continue
                    child = Tree(succ_vbb, succ_vbb.padded_width, succ_vbb.padded_height)
                    current_node.add_child(child)
                    queue.append(child)

        self.root = root
        self.tree_layout = TreeLayout(root)
        self.tree_layout.layout()

    def set_font(
            self,
            block_color,
            title_font,
            title_font_color,
            title_font_matrics,
            content_font,
            content_font_color,
            content_font_matrics,
        ):
        self.block_color = block_color
        self.title_font = title_font
        self.title_font_color = title_font_color
        self.title_font_matrics = title_font_matrics
        self.content_font = content_font
        self.content_font_color = content_font_color
        self.content_font_matrics = content_font_matrics



