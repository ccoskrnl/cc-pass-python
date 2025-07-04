import sys

from PyQt6.QtWidgets import QApplication

from cof.ir import Insts
from cof.cfg import ControlFlowGraph
from cof.cfg.visualizer import CFGVisualizer
from test import testing
if __name__ == "__main__":
    insts: Insts = testing()
    cfg: ControlFlowGraph = ControlFlowGraph(insts)

    app = QApplication(sys.argv)
    window = CFGVisualizer(cfg)
    window.show()
    sys.exit(app.exec())