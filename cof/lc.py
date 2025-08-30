from typing import Optional

from cof.analysis.loop import LoopAnalyzer
from cof.base.cfg import ControlFlowGraph
from cof.base.ssa import SSAEdgeBuilder
from cof.early import EarlyOptimizer


class LocalCodeOptimizer:
    def __init__(self, cfg: ControlFlowGraph):
        self.cfg: Optional[ControlFlowGraph] = cfg
        self.loop_analyzer: Optional[LoopAnalyzer] = None
        self.ssa_edge_builder: Optional[SSAEdgeBuilder] = None

    def initialize(self):
        # control flow graph
        self.cfg.initialize()

        # print(self.cfg.edges)

        # loop analyzer
        self.loop_analyzer = LoopAnalyzer(self.cfg)
        self.loop_analyzer.analyze_loops()

    def optimize(self):


        early_optimizer = EarlyOptimizer(self.cfg)
        # +++++++++++++++++++++ Lazy-Code Motion Analysis +++++++++++++++++++++
        early_optimizer.optimize(method='lazy-code motion')

        # +++++++++++++++++++++ SSA Computing +++++++++++++++++++++
        # self.cfg.minimal_ssa()
        # self.ssa_edge_builder = self.cfg.ssa_edges_comp(self.loop_analyzer)
        # final_insts = MIRInsts(None)


        # +++++++++++++++++++++ SCCP Analysis +++++++++++++++++++++
        # sccp_analyzer: SCCPAnalyzer = sccp_analysis(self.cfg, self.ssa_edge_builder)
        # constant_folding(sccp_analyzer)


        pass