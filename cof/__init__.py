from typing import List, Dict

from cof.analysis.sccp import sccp_analysis
from cof.base.cfg import ControlFlowGraph
from cof.base.mir.function import MIRFunction
from cof.base.mir.inst import MIRInsts
from cof.lc import LocalCodeOptimizer


class CodeOptimizer:

    pre_algorithms : List[str] = ['lcm', 'dae', 'cse', '']
    ssa_period_type: List[str] = ['always', 'never', 'postpone']

    def __init__(
            self,
            insts: MIRInsts,
            func_list: List[MIRFunction],
            sccp_enable: bool,
            pre_algorithm: str,
            ssa_period: str,
            analysis_only: bool = False,
    ):
        self.insts = insts
        self.func_list: List[MIRFunction] = func_list
        self.func_cfg: Dict[MIRFunction, ControlFlowGraph] = { }

        self.pre_algorithm : str = pre_algorithm
        self.ssa_period : str = ssa_period
        self.sccp_enable : bool = sccp_enable
        self.analysis_only : bool = analysis_only

        self._check_params()

    def _check_params(self):
        if self.pre_algorithm not in CodeOptimizer.pre_algorithms:
            self.pre_algorithm = ''
        if self.ssa_period not in CodeOptimizer.ssa_period_type:
            self.ssa_period = 'postpone'


    def optimize(self):
        self.process_local_functions()

    def process_local_functions(self):

        for func in self.func_list:
            print(f"Processing {func.func_name}")
            cfg = ControlFlowGraph(func.insts)
            self.func_cfg[func] = cfg
            lco = LocalCodeOptimizer(
                cfg,
                sccp_enable=self.sccp_enable,
                pre_algorithm=self.pre_algorithm,
                ssa_period=self.ssa_period
            )
            lco.initialize()
            lco.optimize()
            self.insts.assign_addr()

