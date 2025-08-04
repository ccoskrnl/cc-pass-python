import math

from PyQt6.QtCore import Qt, QPointF, QRectF, QEvent
from PyQt6.QtGui import QBrush, QPen, QColor, QTextCursor, QAction, QLinearGradient, QPainterPath, QGradient
from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem, QMenu, QGraphicsSimpleTextItem, \
    QApplication, QGraphicsPathItem

from cof.base.bb import BasicBlock, BasicBlockBranchType, EdgeType
from cof.base.mir import MIRInst


class VisualBasicBlock(BasicBlock):
    def __init__(self, basic_block):
        super().__init__(None, None)
        self.__dict__ = basic_block.__dict__
        self.width_pad = 60
        self.height_pad = 40
        self.padded_height = 0
        self.padded_width = 0
        self.width = 0
        self.height = 0

        self.edge_offset = 0

        self.x = 0
        self.y = 0

        # self.rank = -1
        # self.preorder = -1

        self.tree = None

        self.content = ""
        self.build_content()

        self.content_body_height = 0
        self.content_font = None
        self.content_font_matrics = None
        self.content_font_color = None

        self.title = self.tag
        self.title_height = 25
        self.title_font = None
        self.title_font_matrics = None
        self.title_font_color = None

        self.color = None

        self.succ_vbbs: list[VisualBasicBlock] = []
        self.pred_vbbs: list[VisualBasicBlock] = []

        # A dict, key is vbb that be moved, value is corresponding edge.
        self.edge_dict = { }

    def build_content(self):
        last_inst: MIRInst = self.insts.ret_inst_by_idx(-1)
        addr_width_max = len(str(last_inst.addr))
        for phi_inst in self.insts.ret_phi_insts():
            self.content += " " * (addr_width_max + 2) + str(phi_inst) + "\n"
        for ord_inst in self.insts.ret_ordinary_insts():
            self.content += f"{ord_inst.addr:>{addr_width_max}}: {str(ord_inst)}\n"


class EdgeItem(QGraphicsPathItem):

    # green
    true_branch_color = QColor(0, 153, 0)
    # red
    false_branch_color = QColor(200, 0, 0)
    # black
    un_cond_branch_color = QColor(0, 0, 0)
    # blue
    cross_edge_color = QColor(120, 200, 240)
    # purple
    switch_color = QColor(150, 0, 150)


    def __init__(self, source: VisualBasicBlock, target: VisualBasicBlock):
        super().__init__()
        self.source: VisualBasicBlock = source
        self.target: VisualBasicBlock = target

        self.color = None
        self.connection_type = EdgeType.tree

        match self.source.branch_type:
            case BasicBlockBranchType.jump:
                self.color = EdgeItem.un_cond_branch_color
            case BasicBlockBranchType.cond:
                true_branch_bb_id = self.source.ordered_succ_bbs[0]
                if self.target.id == true_branch_bb_id:
                    self.color = EdgeItem.true_branch_color
                else:
                    self.color = EdgeItem.false_branch_color
            case BasicBlockBranchType.switch:
                self.color = EdgeItem.switch_color

        if self.source.rank == self.target.rank:
            self.color = EdgeItem.cross_edge_color
            self.connection_type = EdgeType.cross

        self.setPen(QPen(self.color, 2))

        # forward edge
        if self.source.rank + 1 < self.target.rank:
            self.connection_type = EdgeType.forward
        # back edge
        elif self.source.rank > self.target.rank:
            self.connection_type = EdgeType.back

        # self.setPen(QPen(QColor(178, 34, 34), 2))
        self.update_path()

    # def add_connection(self):
    #
    #     # the bottom middle position of the source
    #     start_pos = QPointF(
    #         self.source.x + self.source.width / 2,
    #         self.source.y + self.source.height
    #     )
    #     # the top middle position of the target
    #     end_pos = QPointF(
    #         self.target.x + self.target.width / 2,
    #         self.target.y
    #     )


    def update_path(self):


        arrow_base = None

        # 计算起点和终点位置
        start_pos = QPointF(
            self.source.x + self.source.width / 2,
            self.source.y + self.source.height
        )
        start_pos_x: float = self.source.x + self.source.width / 2
        start_pos_y: float = self.source.y + self.source.height

        end_pos = QPointF(
            self.target.x + self.target.width / 2,
            self.target.y
        )

        end_pos_x: float = self.target.x + self.target.width / 2
        end_pos_y: float = self.target.y



        # 计算控制点
        horizontal_offset = min(200, abs(start_pos.x() - end_pos.x()) * 0.3)
        vertical_offset = min(150, abs(start_pos.y() - end_pos.y()) * 0.5)


        # 创建曲线路径
        path = QPainterPath()
        path.moveTo(start_pos)

        if self.connection_type == EdgeType.tree:
            ctrl1 = QPointF(start_pos_x, start_pos_y + vertical_offset)
            ctrl2 = QPointF(end_pos_x, end_pos_y - vertical_offset)
            path.cubicTo(ctrl1, ctrl2, end_pos)
        elif self.connection_type == EdgeType.back:
            control_offset = 300
            if start_pos_x < end_pos_x:
                control1 = QPointF(
                    start_pos_x + control_offset + horizontal_offset
                    , start_pos_y + vertical_offset)
                control2 = QPointF(
                    end_pos_x - control_offset - horizontal_offset
                    , end_pos_y - vertical_offset)
            else:
                control1 = QPointF(
                    start_pos_x - control_offset - horizontal_offset
                    , start_pos_y + vertical_offset)
                control2 = QPointF(
                    end_pos_x + control_offset + horizontal_offset
                    , end_pos_y - vertical_offset)

            path.cubicTo(control1, control2, end_pos)

            arrow_base = control2
        elif self.connection_type == EdgeType.forward:

            offset_x = (end_pos_x - start_pos_x) * 0.3
            offset_y = abs(end_pos_y - start_pos_y) * 0.5

            path.cubicTo(
                start_pos_x + offset_x, start_pos_y + offset_y,
                end_pos_x - offset_x, end_pos_y - offset_y,
                end_pos_x, end_pos_y
            )
        elif self.connection_type == EdgeType.cross:

            # 计算偏移量（避免重叠）
            offset = (end_pos_x - (start_pos_x + self.source.width)) / 2


            path.lineTo(start_pos_x, start_pos_y + 40)
            path.lineTo(end_pos_x - offset - (self.target.width / 2), start_pos_y + 40)
            path.lineTo(end_pos_x - offset - (self.target.width / 2), end_pos_y - 20)
            path.lineTo(end_pos_x, end_pos_y - 20)

            path.lineTo(end_pos_x, end_pos_y)

        self.setPath(path)

        # set arrow
        if not arrow_base:
            self.add_arrow(end_pos, path.pointAtPercent(0.95))
        else:
            self.add_arrow(end_pos, arrow_base)

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
        arrow_item.setBrush(self.color)
        arrow_item.setPen(QPen(Qt.PenStyle.NoPen))

class BlockContentItem(QGraphicsTextItem):
    def __init__(self, block: VisualBasicBlock, parent=None):
        super().__init__(parent)
        self.last_known_cursor_position = None
        self.mouse_press_pos = None
        self.text_select_mode = False
        self.block: VisualBasicBlock = block
        self.height = self.block.content_body_height

        self.setFont(self.block.content_font)
        self.setPlainText(block.content)
        self.setDefaultTextColor(block.content_font_color)

        # allow access to focus
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)

        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditorInteraction |
            Qt.TextInteractionFlag.TextSelectableByMouse |  # type: ignore
            Qt.TextInteractionFlag.TextSelectableByKeyboard  # type: ignore
        )

        self.document().setDocumentMargin(5)  # 内边距
        self.set_fixed_width()


    def set_fixed_width(self):
        # text_width = width - self.document().documentMargin() * 2
        # self.setTextWidth(text_width)
        self.setTextWidth(self.block.width)

    def ensure_cursor_visible(self):
        cursor = self.textCursor()
        self.setTextCursor(cursor)

    def get_cursor_position(self):
        return self.textCursor().position()

    def set_cursor_position(self, position):
        cursor = self.textCursor()
        cursor.setPosition(position)
        self.setTextCursor(cursor)

    def get_selected_text_range(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            return cursor.selectionStart(), cursor.selectionEnd()
        return self.get_cursor_position(), self.get_cursor_position()

    def copy_selected_text(self):
        """复制选中的文本到剪贴板"""
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)

    def get_selected_text(self):
        """获取当前选中的文本"""
        cursor = self.textCursor()
        return cursor.selectedText() if cursor.hasSelection() else ""

    def select_all_text(self):
        """选择所有文本"""
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)

    def select_line_at_cursor(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        self.setTextCursor(cursor)

    def position_at_point(self, point):

        doc_point = QPointF(point.x(), point.y())

        cursor_pos = self.document().documentLayout().hitTest(
            doc_point, Qt.HitTestAccuracy.ExactHit
        )

        return cursor_pos if cursor_pos >= 0 else self.textCursor().position()

    def boundingRect(self):
        """返回文本内容区域的边界矩形"""
        # 返回一个 (0,0,宽度,高度) 的矩形
        return QRectF(0, 0, self.block.width, self.height)

    def paint(self, painter, option, widget=None):
        """绘制文本内容区域"""
        painter.save()
        # 绘制半透明背景
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))  # 半透明白色背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.boundingRect())

        # 绘制顶部和底部的分割线
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawLine(0, 0, int(self.boundingRect().width()), 0)
        painter.drawLine(0, self.height, int(self.boundingRect().width()), self.height)
        painter.restore()

        # 绘制文本
        super().paint(painter, option, widget)

    def keyPressEvent(self, event):
        """处理键盘事件 - 支持选择和复制快捷键"""
        # 处理文本导航
        if event.key() in [Qt.Key.Key_Left, Qt.Key.Key_Right,
                           Qt.Key.Key_Up, Qt.Key.Key_Down,
                           Qt.Key.Key_Home, Qt.Key.Key_End]:
            super().keyPressEvent(event)
            return

        # Ctrl+C 复制
        if event.key() == Qt.Key.Key_C and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.copy_selected_text()
            event.accept()
            return

        # Ctrl+A 全选
        if event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.select_all_text()
            event.accept()
            return

        # ESC 键退出文本选择模式
        if event.key() == Qt.Key.Key_Escape:
            self.text_select_mode = False
            self.clearFocus()
            event.accept()
            return

        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """
            Handle mouse press event - capture
            text select event rather than pass
            to parent window
        """

        if event.buttons() == Qt.MouseButton.LeftButton:
            # Enable text select mode
            self.text_select_mode = True

            self.setFocus(Qt.FocusReason.MouseFocusReason)

            # record initial press position (convert to document position)
            self.mouse_press_pos = event.pos()

            # create new cursor and set position
            cursor = QTextCursor(self.document())
            position = self.position_at_point(self.mouse_press_pos)
            if position >= 0:
                cursor.setPosition(position)

            if event.type() == QEvent.Type.MouseButtonDblClick:
                cursor.select(QTextCursor.SelectionType.WordUnderCursor)

            self.setTextCursor(cursor)

            self.parentItem().setSelected(True)
            self.parentItem().mousePressEvent(event)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move event - only handle text select, but not pass move event"""

        if self.text_select_mode and event.buttons() & Qt.MouseButton.LeftButton:
            # convert to document pos
            mouse_current_pos = event.pos()

            # get current pos corresponding document pos
            end_position = self.position_at_point(mouse_current_pos)
            cursor = self.textCursor()

            # if there is currently a selected range,
            # expand the selection
            if end_position >= 0:
                cursor.setPosition(end_position, QTextCursor.MoveMode.KeepAnchor)
                self.setTextCursor(cursor)

            self.ensure_cursor_visible()

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release - exit text select mode"""
        if event.button() == Qt.MouseButton.LeftButton and self.text_select_mode:
            # Exit text select mode
            self.text_select_mode = False
            self.last_known_cursor_position = self.textCursor().position()

            event.accept()
            return
        super().mouseReleaseEvent(event)

    def focusOutEvent(self, event):
        """exit text select mode when losing focus"""
        self.text_select_mode = False
        super().focusOutEvent(event)

    def hoverEnterEvent(self, event):
        """enter text area when hovering"""
        self.setCursor(Qt.CursorShape.IBeamCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """leave text area"""
        if not self.text_select_mode:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event):
        """显示文本上下文菜单"""
        menu = QMenu()

        # 复制选项
        copy_action: QAction = QAction("Copy", menu)
        copy_action.triggered.connect(self.copy_selected_text)

        # 全选选项
        select_all_action: QAction = QAction("Select All", menu)
        select_all_action.triggered.connect(self.select_all_text)

        # 选择行选项
        select_line_action: QAction = QAction("Select Line", menu)
        select_line_action.triggered.connect(self.select_line_at_cursor)

        # 仅当有选中文本时才启用复制
        copy_action.setEnabled(bool(self.get_selected_text()))

        menu.addAction(copy_action)
        menu.addAction(select_all_action)
        menu.addAction(select_line_action)

        menu.exec(event.screenPos())

class BlockItem(QGraphicsItem):
    def __init__(self, block: VisualBasicBlock):
        super().__init__()
        self.drag_start_position = None
        self.is_dragging = None
        self.block: VisualBasicBlock = block

        # Create Background Rectangle.
        self.rect_item = QGraphicsRectItem(0, 0, block.width, block.height, self)
        self.rect_item.setBrush(QBrush(block.color))
        self.rect_item.setPen(QPen(QColor(180, 240, 200), 1)) # black border

        # Create Title
        self.title_bar = QGraphicsRectItem(0, 0, block.width, block.title_height, self)
        self.title_bar.setBrush(self.create_title_gradient())
        self.title_bar.setPen(QPen(QColor(120, 200, 240), 1)) # black border

        # Create Title Text
        self.title_text = QGraphicsSimpleTextItem(block.title, self)
        self.title_text.setFont(block.title_font)
        self.title_text.setBrush(QBrush(block.title_font_color))
        self.title_text.setPos(5, (block.title_height - self.title_text.boundingRect().height()) / 2)

        # Create Body Text Box
        self.content_item = BlockContentItem(block, self)
        self.content_item.setPos(0, block.title_height)

        # 设置图形项属性
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        # 初始位置
        self.setPos(self.block.x, self.block.y)

    def create_title_gradient(self) -> QLinearGradient:
        """Create a title bar gradient effect"""

        # gradient = QLinearGradient(0, 0, 0, self.block.title_height)
        gradient = QLinearGradient(0, 0, self.block.width, 0)

        gradient.setColorAt(0, QColor(120, 200, 240))
        gradient.setColorAt(0.5, QColor(150, 220, 230))
        gradient.setColorAt(1, QColor(180, 240, 200))

        gradient.setSpread(QGradient.Spread.ReflectSpread)
        return gradient

    def update_connections(self):
        # exit edges
        for edge_item in self.block.edge_dict.values():
            edge_item.update_path()
        # incident edge
        for pred_vbb in self.block.pred_vbbs:
            if self.block.id in pred_vbb.edge_dict:
                incident_edge = pred_vbb.edge_dict[self.block.id]
                incident_edge.update_path()


    def adjust_position_to_avoid_overlap(self):
        for item in self.collidingItems():
            if isinstance(item, BlockItem) and item != self:
                direction = self.scenePos() - item.scenePos()
                direction = direction / direction.manhattanLength() * 5

                self.setPos(self.pos() + direction)
                self.update()

    def shape(self):
        origin_rect: QRectF = self.boundingRect()
        custom_rect: QRectF = QRectF(
            origin_rect.x() - self.block.width_pad,
            origin_rect.y() - self.block.height_pad,
            self.block.padded_width,
            self.block.padded_height
        )
        path = QPainterPath()
        path.addRect(custom_rect)
        return path

    def boundingRect(self):
        return self.rect_item.boundingRect()

    def paint(self, painter, option, widget=None):
        # 组合项不需要直接绘制
        # if self.isSelected():
        #     painter.setPen(QPen(QColor(180, 240, 200), 2))
        pass

    def mousePressEvent(self, event):
        """Handle mouse press event - only start dragging in the title bar"""
        title_rect = QRectF(0, 0, self.block.width, self.block.title_height)
        pos = event.pos()

        if title_rect.contains(pos):
            # title bar has been clicked - start dragging
            self.is_dragging = True
            self.drag_start_position = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.setZValue(1)

    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.is_dragging = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # self.adjust_position_to_avoid_overlap()

            self.setZValue(0)  # 恢复原层级

        super().mouseReleaseEvent(event)

        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            # old_pos = self.pos()
            # calculate distance
            delta = event.pos() - self.drag_start_position
            new_pos = self.pos() + delta
            self.setPos(new_pos)

            self.block.x = new_pos.x()
            self.block.y = new_pos.y()

            self.update_connections()

            # colliding = False
            # for item in self.collidingItems():
            #     if isinstance(item, BlockItem) and item != self:
            #         colliding = True
            #         break


            # if colliding:
            #     self.setPos(old_pos)
            #     event.accept()
            # else:
            #     # update block pos
            #     self.block.position = new_pos
            #     self.update()
            #     # update all connections
            #     self.update_connections()

    def hoverEnterEvent(self, event):
        """处理悬停进入事件"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """处理悬停离开事件"""
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().hoverLeaveEvent(event)