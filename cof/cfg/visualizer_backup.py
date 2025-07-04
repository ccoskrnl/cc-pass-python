import sys
import math
from typing import Dict, Set
from collections import deque, defaultdict

from PyQt6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
                             QGraphicsRectItem, QGraphicsTextItem, QGraphicsPathItem,
                             QGraphicsItem, QMenu, QVBoxLayout, QWidget, QHBoxLayout,
                             QLabel, QStatusBar, QToolBar, QSplitter, QTextEdit,
                             QFontComboBox, QSpinBox)
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QBrush, QPen, QColor, QFont, QPainterPath, QLinearGradient, QAction, QFontMetrics

from . import ControlFlowGraph
from .bb import *

class BlockItem(QGraphicsRectItem):
    def __init__(self, block: BasicBlock):
        super().__init__(0, 0, block.width, block.height)
        self.block = block
        self.setBrush(QBrush(block.color))
        self.setPen(QPen(QColor(255, 255, 255), 2))
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.setRect(0, 0, block.width, block.height)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        self.block.position = self.pos()

        scene: QGraphicsScene | QGraphicsScene = self.scene()
        if scene:
            for item in scene.items():
                if isinstance(item, EdgeItem) \
                    and (item.source == self.block or item.target == self.block):
                    item.update_path()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # update block position
            self.block.position = self.pos()

            scene = self.scene()
            if scene:
                for item in scene.items():
                    if isinstance(item, EdgeItem) \
                        and (item.source == self.block or item.target == self.block):
                        item.update_path()
        return super().itemChange(change, value)

class EdgeItem(QGraphicsPathItem):
    def __init__(self, source: BasicBlock, target: BasicBlock):
        super().__init__()
        self.source = source
        self.target = target
        self.setPen(QPen(QColor(178, 34, 34), 2))
        self.update_path()

    def update_path(self):
        start_pos = QPointF(
            self.source.position.x() + self.source.width / 2,
            self.source.position.y() + self.source.height
        )

        end_pos = QPointF(
            self.target.position.x() + self.target.width / 2,
            self.target.position.y()
        )

        mid_y = (start_pos.y() + end_pos.y()) / 2
        ctrl_dist = min(150, abs(start_pos.y() - end_pos.y()) * 0.5)

        # Create curve path
        path = QPainterPath()
        path.moveTo(start_pos)

        # adjust curve according to direction
        if end_pos.y() > start_pos.y():  # 向下流动
            ctrl1 = QPointF(start_pos.x(), start_pos.y() + ctrl_dist)
            ctrl2 = QPointF(end_pos.x(), end_pos.y() - ctrl_dist)
        else:  # upward
            ctrl1 = QPointF(start_pos.x(), start_pos.y() - ctrl_dist)
            ctrl2 = QPointF(end_pos.x(), end_pos.y() + ctrl_dist)

        path.cubicTo(ctrl1, ctrl2, end_pos)

        # set path
        self.setPath(path)

        # set arrow
        self.add_arrow(end_pos, path.pointAtPercent(0.95))

        return

    def add_arrow(self, tip, base):
        # remove old arrow
        current_scene = self.scene()
        if current_scene and hasattr(current_scene, 'items'):
            for item in self.scene().items():
                if isinstance(item, QGraphicsPathItem) and item.parentItem() == self:
                    self.scene().removeItem(item)

        # calculate direction of arrow
        direction = tip - base
        if direction.x() == 0 and direction.y() == 0:
            return

        # calculate angle
        angle = math.atan2(direction.y(), direction.x())

        # arrow size
        arrow_size = 10

        # create arrow path
        arrow_path = QPainterPath()
        arrow_path.moveTo(tip)

        # arrow point 1
        arrow_path.lineTo(
            tip.x() - arrow_size * math.cos(angle - math.pi/6),
            tip.y() - arrow_size * math.sin(angle - math.pi/6)
        )

        # arrow point 2
        arrow_path.lineTo(
            tip.x() - arrow_size * math.cos(angle + math.pi/6),
            tip.y() - arrow_size * math.sin(angle + math.pi/6)
        )

        arrow_path.closeSubpath()

        # create arrow shape
        arrow_item = QGraphicsPathItem(arrow_path, self)
        arrow_item.setBrush(QColor(178, 34, 34))
        arrow_item.setPen(QPen(Qt.PenStyle.NoPen))

class GraphLayout:
    def __init__(self, entry_block, blocks):
        self.max_rank = None
        self.font_metrics = None
        self.entry_block = entry_block
        self.blocks : Dict = blocks
        self.ranks = { }
        self.positions = { }
        
    def calculate_block_size(self, block: BasicBlock, font_metrics):
        max_width = 0
        for inst in block.insts:
            line = str(inst)
            line_width = font_metrics.horizontalAdvance(line)
            if line_width > max_width:
                max_width = line_width

        # (insts + tag + pad(2))
        block.height = font_metrics.height() * (len(block.insts) + 1 + 2)
        block.width = max_width

        self.font_metrics = font_metrics

    def assign_ranks(self):

        # initialize
        for block in self.blocks.values():
            self.ranks[block.id] = -1

        queue = deque([self.entry_block])
        self.ranks[self.entry_block.id] = 0

        while queue:
            current = queue.popleft()
            current_rank = self.ranks[current.id]

            for succ in current.succ_bbs.values():
                # If the successors not have been allocated rank, or
                # the path gives lesser rank
                if self.ranks[succ.id] < 0 or self.ranks[succ.id] > current_rank + 1:
                    self.ranks[succ.id] = current_rank + 1
                    queue.append(succ)

        self.handle_loops()
        self.max_rank = max(self.ranks.values())

    def handle_loops(self):
        """Handle loop structure layer"""

        back_edges = []
        for block in self.blocks.values():
            for succ in block.succ_bbs.values():
                if self.ranks[succ.id] < self.ranks[block.id]:
                    back_edges.append((block, succ))

        for back_edge in back_edges:
            # The loop header
            header = back_edge[1]

            # The loop tail
            loop_tail = back_edge[0]
            loop_blocks = self.find_loop_blocks(header, loop_tail)

            min_rank = min(self.ranks[b.id] for b in loop_blocks)
            for block in loop_blocks:
                self.ranks[block.id] = min_rank

    def find_loop_blocks(self, header, back_edge_source) -> Set:
        """Find all blocks be contained in loop"""
        loop_blocks = {header, back_edge_source}
        queue = deque([back_edge_source])

        while queue:
            current = queue.popleft()
            for pred in current.pred_bbs.values():
                if pred not in loop_blocks and self.ranks[pred.id] >= self.ranks[header.id]:
                    loop_blocks.add(pred)
                    queue.append(pred)

        return loop_blocks

    def initial_layout(self):
        """Initial layout"""

        # Record each rank corresponds blocks
        rank_groups = defaultdict(list)
        for block_id, rank in self.ranks.items():
            rank_groups[rank].append(self.blocks[block_id])

        # Each layer's height is the highest block.
        layer_heights = { }
        for rank, blocks in rank_groups.items():
            max_height = max(block.height for block in blocks)
            layer_heights[rank] = max_height



        # gap between layers
        layer_spacing = 100

        # each layer's position is the previous layer's height added gap.
        layer_positions = { 0 : 0 }
        for rank in range(1, self.max_rank + 1):
            layer_positions[rank] = layer_positions[rank - 1] + layer_heights[rank - 1] + layer_spacing


        for rank, blocks in rank_groups.items():
            total_width = sum(block.width for block in blocks)
            max_width = max(block.width for block in blocks) if blocks else 0
            block_spacing = max(50, max_width * 0.4)
            total_width += block_spacing * (len(blocks) - 1)

            start_x = -total_width / 2
            current_x = start_x

            # allocate position for each block
            for block in blocks:
                block.x = current_x
                block.y = layer_positions[rank]
                current_x += block.width + block_spacing
                self.positions[block.id] = (block.x, block.y)

    def force_directed_layout(self, iterations=100):

        # Repulsion
        k_repel = 300.0
        # gravity
        k_attract = 0.1
        # damping
        damping = 0.85

        temperature = 10.0
        cooling_factor = 0.95

        for _ in range(iterations):
            forces = { block.id: [0.0, 0.0] for block in self.blocks.values()}
            # calculate repulsion
            blocks = list(self.blocks.values())
            for i, block1 in enumerate(blocks):
                for block2 in blocks[i+1:]:
                    dx = block1.x - block2.x
                    dy = block1.y - block2.y
                    distance = max(1.0, math.sqrt(dx*dx + dy*dy))

                    # Repulsion calculation(inversely proportional to the
                    # square of the distance)
                    force = k_repel / (distance * distance)
                    fx = force * dx / distance
                    fy = force * dy / distance

                    forces[block1.id][0] += fx
                    forces[block1.id][1] += fy
                    forces[block2.id][0] -= fx
                    forces[block2.id][1] -= fy

            for block in blocks:
                for succ in block.succ_bbs.values():
                    dx = succ.x - block.x
                    dy = succ.y - block.y
                    distance = max(1.0, math.sqrt(dx*dx + dy*dy))

                    force = k_attract * distance
                    fx = force * dx / distance
                    fy = force * dy / distance

                    forces[block.id][0] += fx
                    forces[block.id][1] += fy
                    forces[succ.id][0] -= fx
                    forces[succ.id][1] -= fy

            for block_id, (fx, fy) in forces.items():
                block = self.blocks[block_id]

                move_dist = min(temperature, math.sqrt(fx*fx + fy*fy))
                if move_dist > 0:
                    # calculate direction
                    dir_x = fx / move_dist
                    dir_y = fy / move_dist

                    block.x += dir_x * move_dist * 0.1
                    block.y += dir_y * move_dist * 0.1

            temperature *= cooling_factor

        for block in self.blocks.values():
            self.positions[block.id] = (block.x, block.y)

    def layout(self, font_metrics):
        for block in self.blocks.values():
            self.calculate_block_size(block, font_metrics)

        self.assign_ranks()

        self.initial_layout()

        self.force_directed_layout()

        return self.positions

class CFGVisualizer(QMainWindow):
    def __init__(self, cfg: ControlFlowGraph):
        super().__init__()

        self.edge_items = { }
        self.block_items = { }
        self.font_combo = None
        self.size_spinbox = None
        self.cfg = cfg

        self.inst_font = QFont("Maple Mono", 10)
        self.inst_font_metrics = QFontMetrics(self.inst_font)

        self.entry_block = cfg.root
        self.blocks = cfg.vertices

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
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Maple Mono", 12))
        self.text_edit.setPlaceholderText(
            "Control Flow Graph will show in here...")

        self.splitter.addWidget(self.view)
        self.splitter.addWidget(self.text_edit)
        self.splitter.setSizes([600, 200])

        # Layout Engine
        self.layout_engine = None

        # timer for layout animation
        self.layout_timer: QTimer | QTimer = QTimer(self)
        self.layout_timer.timeout.connect(self.animate_layout)
        self.layout_iteration = 0
        self.max_layout_iterations = 100

        # self.create_control_panel()

        self.create_toolbar()

        self.create_cfg()
        self.animate_layout()

    def create_control_panel(self):
        """Create the control panel for the visualizer.
        """
        panel = QHBoxLayout()

        font_label = QLabel("Font:")
        self.font_combo: QFontComboBox | QFontComboBox = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Maple Mono", 12))
        # self.font_combo.currentFontChanged.connect(self.update_font)

        size_label = QLabel("Size:")
        self.size_spinbox: QSpinBox | QSpinBox = QSpinBox()
        self.size_spinbox.setRange(8, 32)
        self.size_spinbox.setValue(12)
        # self.size_spinbox.valueChanged.connect(self.update_font_size)

        panel.addWidget(font_label)
        panel.addWidget(self.font_combo)
        panel.addWidget(size_label)
        panel.addWidget(self.size_spinbox)

        self.layout.addLayout(panel)

    def create_toolbar(self):
        toolbar = self.addToolBar("Tools")

        zoom_in_action: QAction | QAction = QAction("Zoom In", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.setStatusTip("Zoom In")
        zoom_in_action.setToolTip("Zoom In (Ctrl++)")
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action: QAction | QAction = QAction("Zoom Out", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.setStatusTip("Zoom Out")
        zoom_out_action.setToolTip("Zoom Out (Ctrl+-)")
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        toolbar.addSeparator()

        layout_action: QAction | QAction = QAction("Auto Layout", self)
        layout_action.triggered.connect(self.auto_layout)
        toolbar.addAction(layout_action)

        reset_action: QAction | QAction = QAction("Reset Layout", self)
        reset_action.triggered.connect(self.reset_view)
        toolbar.addAction(reset_action)

        toolbar.addSeparator()

        help_action: QAction | QAction = QAction("Help", self)
        help_action.triggered.connect(self.show_help)
        toolbar.addAction(help_action)

    def zoom_in(self):
        # guarantee view exists
        if hasattr(self, 'view') and self.view:
            self.view.scale(1.2, 1.2)

    def zoom_out(self):
        if hasattr(self, 'view') and self.view:
            self.view.scale(0.8, 0.8)

    def show_help(self):
        help_text = """
        <h2>控制流图可视化工具使用说明</h2>
        <p><b>基本操作：</b></p>
        <ul>
            <li><b>拖动基本块</b>：用鼠标左键拖动基本块重新定位</li>
            <li><b>查看块信息</b>：右键点击基本块查看详细信息</li>
            <li><b>放大/缩小</b>：使用工具栏按钮或鼠标滚轮缩放视图</li>
            <li><b>自动布局</b>：点击"自动布局"按钮重新排列基本块</li>
        </ul>
        <p><b>视图控制：</b></p>
        <ul>
            <li><b>平移视图</b>：按住空格键并拖动鼠标</li>
            <li><b>框选多个块</b>：在空白处拖动鼠标创建选择框</li>
        </ul>
        """
        self.text_edit.setHtml(help_text)
        self.status_bar.showMessage("显示帮助信息")

    def layout_blocks(self):
        layers = defaultdict(List)
        n_layer = 0
        node = self.cfg.root

        # loop while node has successors.
        while node.succ_bbs:
            layers[n_layer].extend([v for k, v in node.succ_bbs])
            n_layer += 1

        layer_heights = {}

    def reset_view(self):
        self.view.resetTransform()
        self.view.centerOn(0, 0)
        self.status_bar.showMessage("View has been reset")

    def auto_layout(self):
        return self

    def create_cfg(self):

        self.layout_engine = GraphLayout(self.entry_block, self.blocks)

        positions = self.layout_engine.layout(self.inst_font_metrics)

        # visualize block
        for block_id, (x, y) in positions.items():
            block = self.blocks[block_id]
            block.position = QPointF(x, y)
            self.create_block(block)

        # visualize edge
        for block in self.blocks.values():
            for succ in block.succ_bbs.values():
                self.create_edge(block, succ)

    def animate_layout(self):
        if self.layout_iteration >= self.max_layout_iterations:
            self.layout_timer.stop()
            return

        # execute once
        self.layout_engine.force_directed_layout(iterations=1)

        for block_id, (x, y) in self.layout_engine.positions.items():
            block = self.blocks[block_id]
            block.position = QPointF(x, y)

            if block_id in self.block_items:
                rect_item = self.block_items[block_id]
                rect_item.setPos(block.position)

        for edge in self.edge_items.values():
            edge.update_path()

        self.layout_iteration += 1

    def create_block(self, block: BasicBlock):
        """create block sharp(support dynamic size)"""


        # set block body color
        block.color = QColor(67, 205, 128)

        # create rectangle sharp as container
        rect_item = BlockItem(block)
        rect_item.setPos(block.position)

        # set item flags
        rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        rect_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        # set z-axis
        rect_item.setZValue(2)

        # add to scene
        self.scene.addItem(rect_item)

        # title
        title_text = QGraphicsTextItem(block.tag, rect_item)
        title_text.setDefaultTextColor(Qt.GlobalColor.black)
        title_text.setFont(self.inst_font)

        text_width = title_text.boundingRect().width()
        text_x = (block.width - text_width) / 2
        title_text.setPos(text_x, 3)

        # content_y =


        # label_item = QGraphicsTextItem(block.tag, rect_item)
        # label_item.setDefaultTextColor(Qt.GlobalColor.white)
        # label_item.setFont(QFont("Arial", 12))
        # label_item.setPos(10, 10)
        # label_item.setZValue(3)

        text_y = 10
        for i, instr in enumerate(block.insts):
            instr_item = QGraphicsTextItem(str(instr), rect_item)
            instr_item.setDefaultTextColor(Qt.GlobalColor.black)
            instr_item.setFont(QFont("Maple Mono", 10))
            instr_item.setPos(10, text_y)
            instr_item.setZValue(3)
            text_y += 20

        self.block_items[block.id] = rect_item
        return rect_item

    def create_edge(self, source: BasicBlock, target: BasicBlock):
        edge_item = EdgeItem(source, target)
        edge_item.setZValue(1)
        self.scene.addItem(edge_item)

        self.edge_items[(source.id, target.id)] = edge_item
        return edge_item