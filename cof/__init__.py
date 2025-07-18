import sys

from PyQt6.QtWidgets import QApplication

from cof.ir import MIRInsts
from cof.cfg import ControlFlowGraph
from cof.cfg.visualizer import CFGVisualizer
from cof.loop import LoopAnalyzer


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

    def initialize_optimizer(self):
        self.cfg.__built__()
        self.cfg.minimal_ssa()

        self.loop_analyzer.analyze_loops()
        self.cfg.ssa_edges_comp()


