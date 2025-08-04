from typing import Optional

from cof.analysis.dataflow import DataFlowAnalyzer
from cof.analysis.loop import LoopAnalyzer
from cof.base.ssa import SSAEdgeBuilder
from cof.base.cfg import ControlFlowGraph
from cof.analysis.sccp import sccp_analysis, SCCPAnalyzer
from cof.early.const_folding import constant_folding
from cof.base.mir import MIRInsts


class LocalCodeOptimizer:
    def __init__(self, **kwargs):
        self.insts: MIRInsts = kwargs['insts']
        self.cfg: Optional[ControlFlowGraph] = None
        self.loop_analyzer: Optional[LoopAnalyzer] = None
        self.ssa_edge_builder: Optional[SSAEdgeBuilder] = None

    def initialize(self):
        # control flow graph
        self.cfg = ControlFlowGraph(self.insts)
        self.cfg.initialize()

        # loop analyzer
        self.loop_analyzer = LoopAnalyzer(self.cfg)
        self.loop_analyzer.analyze_loops()

    def optimize(self):
        analyzer = DataFlowAnalyzer(cfg=self.cfg)
        analyzer.reaching_definitions()

        # # SSA computing
        # self.cfg.minimal_ssa()
        # self.ssa_edge_builder = self.cfg.ssa_edges_comp(self.loop_analyzer)
        # final_insts = MIRInsts(None)
        #
        #
        # sccp_analyzer: SCCPAnalyzer = sccp_analysis(self.cfg, self.ssa_edge_builder)
        # constant_folding(sccp_analyzer)
        # # dce_insts = control_flow_dce(sccp_analyzer)
        # #
        # # final_insts = dce_insts
        # return final_insts

