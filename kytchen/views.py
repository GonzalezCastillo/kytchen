from PyQt6.QtCore import (
    QAbstractTableModel, Qt, QSortFilterProxyModel, pyqtSignal,
    QModelIndex, QEvent
)
from PyQt6.QtWidgets import (
    QTableView, QMenu, QHeaderView, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLineEdit, QStyledItemDelegate, QStyle, QStyleOptionButton,
    QApplication, QMessageBox, QInputDialog, QLabel, QAbstractItemView
)
from PyQt6.QtGui import QFont
from decimal import Decimal

def num(value):
    value = Decimal(value)
    if value < 0:
        raise ValueError("expected non-negative amount")
    return value

def show_error(view, msg):
    msg_box = QMessageBox(view)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Error")
    msg_box.setText(msg)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()

def create_new(parent, object_id, create_function):
    ok = True
    context = ""
    while ok:
        msg = context + f"Please enter the new {object_id} ID:"
        try_id, ok = QInputDialog.getText(parent, f"New {object_id}", msg)
        if try_id.strip() == "":
            context = "You cannot provide an empty ID.\n"
            continue
        if create_function(try_id):
            break
        else:
            context = f"The ID '{try_id}' is assigned to another component.\n"

def general_margin(view):
    view.setContentsMargins(15, 15, 15, 15)

def no_margin(view):
    view.setContentsMargins(0,0,0,0)

def Title(text):
    view = QLabel(text)
    font = QFont()
    font.setPointSize(20)
    font.setBold(True)
    view.setFont(font)
    return view

def Subtitle(text):
    view = QLabel(text)
    font = QFont()
    font.setPointSize(14)
    font.setBold(True)
    view.setFont(font)
    return view

class ClickLabel(QLabel):
    clicked = pyqtSignal()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

class CoreTableModel(QAbstractTableModel):
    header_names = []
    align = []
    not_editable = []

    def __init__(self, parent, content):
        super().__init__(parent)
        self.content = content
        self.ncols = len(self.header_names)

    def rowCount(self, parent = None):
        return len(self.content)

    def columnCount(self, parent = None):
        return self.ncols

    def get_data(self, row, col):
        return None

    def deep_data(self, row, col, is_display):
        return self.get_data(row, col)

    def data(self, index, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = self.align[index.column()]
            if align == "right":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
            elif align == "left":
                return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            else:
                return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self.deep_data(index.row(), index.column(), role == Qt.ItemDataRole.DisplayRole)

    def headerData(self, section, orientation, role = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Vertical:
                return ""
            elif orientation == Qt.Orientation.Horizontal:
                return self.header_names[section] 
        return None

    def set_data(self, row, col, value):
        return True

    def update_row(self, row):
        index0 = self.index(row, 0)
        index1 = self.index(row, self.ncols - 1)
        self.dataChanged.emit(index0, index1)

    def update_col(self, col):
        index0 = self.index(0, col)
        index1 = self.index(len(self.content) - 1, col)
        self.dataChanged.emit(index0, index1)

    def real_index(self, index):
        return index

    def setData(self, index, value, role = Qt.ItemDataRole.EditRole):
        if not index.isValid() or not role == Qt.ItemDataRole.EditRole:
            return False
        changed = self.set_data(index.row(), index.column(), value)
        if not changed:
            return False
        self.dataChanged.emit(index, index)
        return True        

    def flags(self, index):
        index = self.real_index(index)
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() in self.not_editable:
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

    def new_entry(self):
        return None

    def general_new_row(self):
        self.beginResetModel() 
        self.new_entry()
        self.endResetModel()

    def delete_entry(self, row):
        return None

    def general_delete_row(self, index, by_row = False):
        if by_row:
            index = self.index(index, 0)
        index = self.real_index(index)
        index = index.row()
        self.beginRemoveRows(QModelIndex(), index, index)
        self.delete_entry(index)
        self.endRemoveRows()

class CoreTable(QWidget):
    ModelClass = CoreTableModel
    item_name = ""
    default_widths = []
    fixed_widths = []
    stretch_widths = []
    def __init__(self, content):
        super().__init__()
        self.table = QTableView()
        self.model = self.ModelClass(self.table, content)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        for row, width in self.default_widths:
            self.table.setColumnWidth(row, width)
        for row in self.fixed_widths:
            self.table.horizontalHeader().setSectionResizeMode(row, QHeaderView.ResizeMode.Fixed)
        for row in self.stretch_widths:
            self.table.horizontalHeader().setSectionResizeMode(row, QHeaderView.ResizeMode.Stretch)

        self.layout = QVBoxLayout()
        no_margin(self.layout)
        self.layout.setSpacing(0)
        self.layout.addWidget(self.table)

        if self.item_name != None:
            self.table.customContextMenuRequested.connect(self.open_menu)
            add_button = QPushButton("+")
            add_button.clicked.connect(lambda: self.model.general_new_row())

            self.control_bar_widget = QWidget()          # <- container for HBox
            self.control_bar = QHBoxLayout(self.control_bar_widget)
            general_margin(self.control_bar)
            self.control_bar.addStretch()
            self.control_bar.addWidget(add_button)

            self.layout.addWidget(self.control_bar_widget)
            self.is_editable = True
        else:
            self.is_editable = False

        self.setLayout(self.layout)

    def open_menu(self, position):
        if not self.is_editable:
            return None

        menu = QMenu()
        index = self.table.indexAt(position)

        if index.isValid():
            remove_action = menu.addAction(f"Remove {self.item_name}")
            remove_action.triggered.connect(lambda: self.model.general_delete_row(index))
            menu.addSeparator()

        new_transaction = menu.addAction(f"New {self.item_name}")
        new_transaction.triggered.connect(lambda: self.model.general_new_row())

        menu.exec(self.table.viewport().mapToGlobal(position))

    def keyPressEvent(self, event):
        if self.is_editable and event.key() == Qt.Key.Key_Delete:
            selected_indexes = self.table.selectedIndexes()
            if selected_indexes:
                row_to_delete = selected_indexes[0].row()
                self.model.general_delete_row(row_to_delete, True)
        else:
            super().keyPressEvent(event)

    def set_editable(self, edit):
        if self.item_name == None:
            return 
        self.is_editable = edit
        if edit:
            self.table.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        else:
            self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.control_bar_widget.setVisible(edit)

class ReverseSortProxy(QSortFilterProxyModel):
    def lessThan(self, left, right):
        return not super().lessThan(left, right)

class SortTableModel(CoreTableModel):
    def __init__(self, parent, content):
        super().__init__(parent, content)
        self.proxy = None
    
    def real_index(self, index):
        if self.proxy != None:
            return self.proxy.mapFromSource(index)
        else:
            return index

    def set_proxy(self, proxy):
        self.proxy = proxy

class SortTable(CoreTable):
    ModelClass = SortTableModel
    def __init__(self, content):
        super().__init__(content)
        sort_model = ReverseSortProxy(self.table)
        sort_model.setSourceModel(self.model)
        sort_model.setDynamicSortFilter(True)
        sort_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        sort_model.setFilterKeyColumn(-1)
        self.model.set_proxy(sort_model)

        search_box = QLineEdit()
        search_box.setPlaceholderText("Search...")
        search_box.setMinimumHeight(35)
        search_box.textChanged.connect(sort_model.setFilterFixedString)
        self.layout.insertWidget(0, search_box)

        self.table.setModel(sort_model)
        self.table.setSortingEnabled(True)

class ButtonDelegate(QStyledItemDelegate):

    clicked = pyqtSignal(QModelIndex)

    def paint(self, painter, option, index):

        button = QStyleOptionButton()
        button.rect = option.rect
        button.text = "Open"
        button.state = (
            QStyle.StateFlag.State_Enabled
            | (QStyle.StateFlag.State_Sunken
               if option.state & QStyle.StateFlag.State_Selected
               else QStyle.StateFlag.State_Raised)
        )
        QApplication.style().drawControl(
                QStyle.ControlElement.CE_PushButton, button, painter
        )

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            rect = option.rect
            if rect.contains(event.pos()):
                self.clicked.emit(index)
                return True
        return False

class DashboardTableModel(SortTableModel):
    def action(self, index):
        if not index.isValid():
            return None
        index = self.real_index(index)
        self.content[index.row()].get_window()

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == self.ncols - 1:
                return "" 
    
        return super().data(index, role)

class DashboardTable(SortTable):
    def __init__(self, content):
        super().__init__(content)
        delegate = ButtonDelegate()
        self.table.setItemDelegateForColumn(self.model.ncols - 1, delegate)
        delegate.clicked.connect(self.model.action)

class FixTable(CoreTable):
    def __init__(self, content):
        super().__init__(content)

        self.up_button = QPushButton("Move up")
        self.down_button = QPushButton("Move down")
        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)

        self.up_button.setVisible(False)
        self.down_button.setVisible(False)
        self.table.selectionModel().selectionChanged.connect(self.update_buttons)

        self.control_bar.insertWidget(0, self.up_button)
        self.control_bar.insertWidget(0, self.down_button)

        self.data = self.model.content

    def update_buttons(self):
        row_selected = self.table.selectionModel().hasSelection()
        self.up_button.setVisible(row_selected)
        self.down_button.setVisible(row_selected)

    def move_up(self):
        index = self.table.currentIndex()
        row = index.row()
        if row > 0:
            self.model.beginMoveRows(QModelIndex(), row, row, QModelIndex(), row - 1)
            self.data[row - 1], self.data[row] = self.data[row], self.data[row - 1]
            self.model.endMoveRows()
            self.table.selectRow(row - 1)

    def move_down(self):
        index = self.table.currentIndex()
        row = index.row()
        if row < len(self.data) - 1:
            self.model.beginMoveRows(QModelIndex(), row, row, QModelIndex(), row + 2)
            self.data[row + 1], self.data[row] = self.data[row], self.data[row + 1]
            self.model.endMoveRows()
            self.table.selectRow(row + 1)


