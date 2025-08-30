from typing import List, Dict

from cof.base.cfg import ControlFlowGraph
from cof.base.mir.function import MIRFunction
from cof.base.mir.inst import MIRInsts
from cof.lc import LocalCodeOptimizer


class CodeOptimizer:
    def __init__(self, insts: MIRInsts, func_list: List[MIRFunction]):
        self.insts = insts
        self.func_list: List[MIRFunction] = func_list
        self.func_cfg: Dict[MIRFunction, ControlFlowGraph] = { }

    def process_local_func(self):
        for func in self.func_list:
            cfg = ControlFlowGraph(func.insts)
            self.func_cfg[func] = cfg
            lco = LocalCodeOptimizer(cfg)
            lco.initialize()
            lco.optimize()

        self.insts.assign_addr()
