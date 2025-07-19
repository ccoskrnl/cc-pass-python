import sys

from PyQt6.QtWidgets import QApplication

from cof.early.sccp import SCCPOptimizer, sccp_optimize
from cof.ir.mir import MIRInsts
from cof.cfg import ControlFlowGraph
from cof.cfg.visualizer import CFGVisualizer
from cof.analysis.loop import LoopAnalyzer
from cof.analysis.ssa import SSAEdgeBuilder


class CodeOptimizer:
    def __init__(self, **kwargs):
        self.insts: MIRInsts = kwargs['insts']
        self.cfg = ControlFlowGraph(self.insts)
        self.loop_analyzer = LoopAnalyzer(self.cfg)

    def visualize_cfg(self):
        app = QApplication(sys.argv)
        window = CFGVisualizer(self.cfg)
        window.show()
        sys.exit(app.exec())

    def optimize(self):
        self.cfg.build()
        self.cfg.minimal_ssa()

        self.loop_analyzer.analyze_loops()
        ssa_builder: SSAEdgeBuilder = self.cfg.ssa_edges_comp(self.loop_analyzer)

        sccp_optimize(self.cfg, ssa_builder)


