from typing import List, Dict

from cof.base.cfg import ControlFlowGraph
from cof.base.mir.inst import MIRInsts


class GlobalCodeOptimizer:
    def __init__(self, insts: MIRInsts):
        self.insts = insts
        self.cfgs: Dict[str, ControlFlowGraph] = { }

    def build_cfgs(self):
        pass
