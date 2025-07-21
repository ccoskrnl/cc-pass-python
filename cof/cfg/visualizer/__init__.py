import sys
from typing import Dict

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics
from PyQt6.QtWidgets import (QMainWindow, QGraphicsView, QGraphicsScene,
                             QVBoxLayout, QWidget, QStatusBar, QSplitter, QApplication)

from .tree_layout import CFGLayout, Tree, TreeLayout
from .vbb import VisualBasicBlock, BlockItem, EdgeItem
from .. import ControlFlowGraph


class CFGVisualizer(QMainWindow):
    def __init__(self, cfg: ControlFlowGraph):
        super().__init__()

        self.cfg = cfg

        self.edge_items = { }
        self.block_items = { }
        self.font_combo = None
        self.size_spinbox = None

        self.block_color = QColor(230, 230, 230)

        self.inst_font_color = QColor(0, 0, 0)
        self.inst_font = QFont("Maple Mono NF", 13)
        self.inst_font_metrics = QFontMetrics(self.inst_font)

        self.title_font_color = QColor(255, 255, 255)
        self.title_font = self.inst_font
        self.title_font_metrics = self.inst_font_metrics

        self.blocks: Dict[int, VisualBasicBlock] = { }
        self.copy_basic_blocks(cfg)
        self.entry_block: VisualBasicBlock = self.blocks[cfg.root.id]

        self.setWindowTitle("Control Flow Graph Visualizer")
        self.setGeometry(100, 100, 1600, 900)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Main widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # Layout
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Splitter
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.layout.addWidget(self.splitter)

        # View
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Scene
        self.scene = QGraphicsScene()
        self.scene.setBackgroundBrush(QColor(240, 240, 240))
        self.view.setScene(self.scene)

        # Text Editor
        # self.text_edit = QTextEdit()
        # self.text_edit.setFont(QFont("Maple Mono", 12))
        # self.text_edit.setPlaceholderText(
        #     "Control Flow Graph will show in here...")

        self.splitter.addWidget(self.view)
        # self.splitter.addWidget(self.text_edit)
        # self.splitter.setSizes([600, 200])

        # Layout Engine
        self.layout_engine = None

        # self.create_control_panel()
        #
        # self.create_toolbar()
        #
        self.create_cfg()
        # self.testing(0, 0)
        # self.testing(100, 100)

    def create_cfg(self):

        self.layout_engine = CFGLayout(self.cfg, self.entry_block, self.blocks)
        self.layout_engine.set_font(
            self.block_color,
            self.title_font,
            self.title_font_color,
            self.title_font_metrics,
            self.inst_font,
            self.inst_font_color,
            self.inst_font_metrics,
        )
        self.layout_engine.initialize_cfg_layout()
        self.layout_engine.layout()
        self.visualize_tree(self.layout_engine.root)


        # visualize edge
        for block in self.blocks.values():
            for succ in block.succ_vbbs:
                self.create_edge(block, succ)

    def visualize_tree(self, node: Tree):
        node.vbb.x = node.x
        node.vbb.y = node.y
        node_item = self.create_block(node.vbb)
        self.block_items[node] = node_item

        for child in node.children:
            self.visualize_tree(child)

    def create_block(self, block: VisualBasicBlock) -> BlockItem:
        block_item = BlockItem(block)
        self.scene.addItem(block_item)
        return block_item

    def create_edge(self, source: VisualBasicBlock, dest: VisualBasicBlock):
        edge_item = EdgeItem(source, dest)
        edge_item.setZValue(1)
        self.scene.addItem(edge_item)

        source.edge_dict[dest.id] = edge_item


    def copy_basic_blocks(self, cfg: ControlFlowGraph):
        vertexes = cfg.blocks
        for k, v in vertexes.items():
            self.blocks[k] = VisualBasicBlock(v)


        visual_basic_block: VisualBasicBlock
        for visual_basic_block in self.blocks.values():
            for bb_id in visual_basic_block.succ_bbs:
                visual_basic_block.succ_vbbs.append(self.blocks[bb_id])
            for bb_id in visual_basic_block.pred_bbs:
                visual_basic_block.pred_vbbs.append(self.blocks[bb_id])

    def testing(self, width, height, x, y):
        entry: VisualBasicBlock = self.entry_block
        entry.position = QPointF(x, y)

        font = QFont("Maple Mono NF", 10, QFont.Weight.Bold)
        fm = QFontMetrics(font)

        entry.content_font = font
        entry.content_font_matrics = fm
        entry.title_font = font
        entry.title_font_matrics = fm

        entry.title = "B1 [addr_0]"
        entry.content = "k := false\nj := 2\ni := 1\n"

        color = QColor(255, 255, 255)
        black = QColor(10, 10, 10)
        entry.title_font_color = color
        entry.content_font_color = black
        entry.color = black

        entry.width = width
        entry.height = height

        entry.padded_height = height + 20
        entry.padded_width = width + 20

        entry.title_height = 25
        entry.content_body_height = entry.height - entry.title_height

        return entry
        # block_item = BlockItem(entry)
        #
        # self.scene.addItem(block_item)


def visualize_cfg(cfg: ControlFlowGraph):
    app = QApplication(sys.argv)
    window = CFGVisualizer(cfg)
    window.show()
    sys.exit(app.exec())