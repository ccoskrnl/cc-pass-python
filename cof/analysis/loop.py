from collections import defaultdict
from typing import Optional, List, Dict

from cof.base.cfg import BasicBlock, BasicBlockId


class Loop:
    """
    Loop Structure
    """
    def __init__(self, header: BasicBlock):
        self.header: BasicBlock = header
        self.body_blocks: set[BasicBlock] = set()
        self.latches = set()
        self.parent: Optional['Loop'] = None
        self.children = [ ]

    def add_block(self, block: BasicBlock):
        self.body_blocks.add(block)

    def contains_block(self, block):
        return block in self.body_blocks

    def is_inner_relative_to(self, other: 'Loop'):
        """
        Check whether it is more nested than another loop
        :param other:
        :return:
        """

        # if other is an ancestor of this loop, then
        # this loop is nested deeper

        current = self
        while current.parent:
            if current.parent == other:
                return True
            current = current.parent

        return False

    def __repr__(self):
        return f"Loop(header={self.header}, blocks={len(self.body_blocks)})"


class LoopAnalyzer:
    """
    Loop Analyzer
    """

    def __init__(self, cfg: 'ControlFlowGraph'):
        self.cfg: 'ControlFlowGraph' = cfg
        self.loops = [ ]

    def analyze_loops(self) -> 'LoopAnalyzer':
        """
        analysing loop structure in cfg.
        :return:
        """
        self._find_natural_loops()
        self._compute_loop_nesting()
        return self

    def _find_natural_loops(self):
        """
        find natural loops
        :return:
        """

        # recognize back edges
        header_to_latches: Dict[BasicBlock, List[BasicBlock]] = defaultdict(list)
        for bb in self.cfg.block_by_id.values():
            for succ in bb.succ_bbs.values():
                if self.cfg.ranks[succ.id] < self.cfg.ranks[bb.id]:
                    header_to_latches[succ].append(bb)

        for header, latches in header_to_latches.items():
            loop = Loop(header)
            loop.add_block(header)
            loop.latches.update(latches)

            # add loop body
            worklist: List[BasicBlock] = list(latches)
            visited: set[BasicBlockId] = set()

            while worklist:
                current = worklist.pop(0)
                if current.id in visited:
                    continue
                visited.add(current.id)

                if current.id != header.id and current not in loop.body_blocks:
                    loop.add_block(current)

                for pred in current.pred_bbs.values():
                    if pred.id != header.id and pred.id not in visited:
                        worklist.append(pred)

            self.loops.append(loop)

    def _compute_loop_nesting(self):
        """Calculate loop nesting relationship"""

        # Sort by loop body size ( from small to large)
        self.loops.sort(key=lambda loop: len(loop.body_blocks))

        # establish nesting relationship
        for i, inner_loop in enumerate(self.loops):
            for j in range(i + 1, len(self.loops)):
                outer_loop = self.loops[j]
                if inner_loop.header in outer_loop.body_blocks:
                    inner_loop.parent = outer_loop
                    outer_loop.children.append(inner_loop)

    def get_loop_for_block(self, block: BasicBlock) -> Optional[Loop]:
        """Get innermost loop containing specific block"""

        candidate = None
        for loop in self.loops:
            if loop.contains_block(block):
                # prioritize choosing a deeper loop
                if not candidate or loop.is_inner_relative_to(candidate):
                    candidate = loop
        return candidate