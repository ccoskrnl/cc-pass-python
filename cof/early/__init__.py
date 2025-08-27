from cof.base.cfg import ControlFlowGraph
from cof.early.lazy_code_motion import lazy_code_motion_optimize


class EarlyOptimizer:
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg = cfg

    def optimize(self, method: str):

        match method:
            case 'lazy-code motion':
                lazy_code_motion_optimize(self.cfg)
            case _:
                return