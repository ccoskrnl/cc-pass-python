from typing import Optional

from cof.analysis.loop import LoopAnalyzer
from cof.analysis.sccp import SCCPAnalyzer, sccp_analysis
from cof.base.cfg import ControlFlowGraph
from cof.base.ssa import SSAEdgeBuilder
from cof.early import EarlyOptimizer
from cof.early.const_folding import constant_folding
from utils.cfg_visualizer import visualize_cfg

class LocalCodeOptimizer:
    def __init__(
            self,
            cfg: ControlFlowGraph,
            sccp_enable: bool,
            pre_algorithm: str,
            ssa_period: str,
            analysis_only: bool = False,
    ):
        self.cfg: Optional[ControlFlowGraph] = cfg
        self.loop_analyzer: Optional[LoopAnalyzer] = None
        self.ssa_edge_builder: Optional[SSAEdgeBuilder] = None

        self.pre_algorithm : str = pre_algorithm
        self.ssa_period : str = ssa_period
        self.sccp_enable : bool = sccp_enable
        self.analysis_only : bool = analysis_only

    def initialize(self):
        # control flow graph
        self.cfg.initialize()

        # print(self.cfg.edges)

        # loop analyzer
        self.loop_analyzer = LoopAnalyzer(self.cfg)
        self.loop_analyzer.analyze_loops()

    def optimize(self):

        # +++++++++++++++++++++ SSA Computing +++++++++++++++++++++
        self.cfg.minimal_ssa()
        self.ssa_edge_builder = self.cfg.ssa_edges_comp(self.loop_analyzer)
        print("SSA From: ")
        print(self.cfg.insts)

        if self.sccp_enable:
            # +++++++++++++++++++++ SCCP Analysis +++++++++++++++++++++
            sccp_analyzer: SCCPAnalyzer = sccp_analysis(self.cfg, self.ssa_edge_builder)
            constant_folding(sccp_analyzer)


        match self.pre_algorithm:
            case 'lcm':
                early_optimizer = EarlyOptimizer(self.cfg)
                # +++++++++++++++++++++ Lazy-Code Motion Analysis +++++++++++++++++++++
                early_optimizer.optimize(method='lazy-code motion')
            case 'cse':
                pass
            case 'dae':
                pass

        print(self.cfg.insts)

        pass