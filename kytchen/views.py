from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Iterable, Optional, Union, cast

if TYPE_CHECKING:
    from .ingredient import Ingredient
    from .mealplan import Mealplan
    from .recipe import Recipe

import math

from PyQt6.QtCore import (
    QAbstractTableModel,
    Qt,
    QSortFilterProxyModel,
    pyqtSignal,
    QLocale,
    QObject,
    QModelIndex,
    QEvent,
    QAbstractItemModel,
    QPoint,
    QItemSelectionModel,
    QRect,
    QSize,
)
from PyQt6.QtWidgets import (
    QTableView,
    QMenu,
    QHeaderView,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionButton,
    QApplication,
    QMessageBox,
    QInputDialog,
    QLabel,
    QAbstractItemView,
    QLayout,
    QStyleOptionViewItem,
    QComboBox,
    QPlainTextEdit,
    QDoubleSpinBox,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontMetrics,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPalette,
    QShortcut,
    QTextCursor,
    QTextDocument,
)
from decimal import Decimal, ROUND_HALF_UP

Numeric = Union[Decimal, int, float, str]


def num(value: Numeric) -> Decimal:
    value = Decimal(value)
    if not value.is_finite():
        raise ValueError("expected finite amount")
    if value < 0:
        raise ValueError("expected non-negative amount")
    return value


def num_string(value: Decimal) -> str:
    decimals = max(0, min(2, 3 - len(str(int(value)))))
    rounded = value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    if decimals == 0:
        return f"{rounded:f}"
    return f"{rounded:f}".rstrip("0").rstrip(".")


def exact_string(value: Decimal) -> str:
    return f"{value.normalize():f}"


def json_number(value: Decimal) -> Union[int, float]:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def amount_string(amount: str, unit: str) -> str:
    if unit[:1].isdigit():
        return f"{amount} × {unit}"
    return f"{amount} {unit}".strip()


def metric_strings(values: dict[str, Decimal], per: str = "") -> list[str]:
    return [f"{num_string(value)} {metric}{per}" for metric, value in values.items()]


def show_error(view: Optional[QWidget], msg: str) -> None:
    msg_box = QMessageBox(view)
    msg_box.setIcon(QMessageBox.Icon.Critical)
    msg_box.setWindowTitle("Error")
    msg_box.setText(msg)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def symbol_button(symbol: str, tooltip: str) -> QPushButton:
    button = QPushButton(symbol)
    button.setToolTip(tooltip)
    button.setFixedWidth(30)
    return button


def ask_confirmation(view: Optional[QWidget], msg: str, action: str = "Delete") -> bool:
    msg_box = QMessageBox(view)
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle("Confirm")
    msg_box.setText(msg)
    confirm_button = msg_box.addButton(action, QMessageBox.ButtonRole.DestructiveRole)
    msg_box.setDefaultButton(msg_box.addButton(QMessageBox.StandardButton.Cancel))
    msg_box.exec()
    return msg_box.clickedButton() is confirm_button


def component_choices(components: Iterable[Any]) -> dict[str, str]:
    choices: dict[str, str] = {}
    for component in components:
        label = component.choice_label()
        unique, count = label, 2
        while unique in choices:
            unique = f"{label} [{count}]"
            count += 1
        choices[unique] = component._id
    return choices


def ask_choice(
    parent: Optional[QWidget], title: str, msg: str, choices: dict[str, str]
) -> Optional[str]:
    items = sorted(choices, key=str.lower)
    text, ok = QInputDialog.getItem(parent, title, msg, items, 0, True)
    text = text.strip()
    if not ok or text == "":
        return None
    for candidates in (
        [label for label in items if label.lower() == text.lower()],
        [label for label in items if label.lower().startswith(text.lower() + " (")],
    ):
        if len(candidates) == 1:
            return choices[candidates[0]]
    show_error(
        parent,
        f"Could not find '{text}'. Please choose one of the options in the list.",
    )
    return None


def ask_name(parent: Optional[QWidget], object_name: str) -> Optional[str]:
    context = ""
    while True:
        name, ok = QInputDialog.getText(
            parent,
            f"New {object_name}",
            context + f"Please enter the name of the new {object_name}:",
        )
        if not ok:
            return None
        if name.strip() != "":
            return name.strip()
        context = "You cannot provide an empty name.\n"


def general_margin(view: Union[QWidget, QLayout]) -> None:
    view.setContentsMargins(15, 15, 15, 15)


def no_margin(view: Union[QWidget, QLayout]) -> None:
    view.setContentsMargins(0, 0, 0, 0)


def Title(text: str, size: int = 20) -> QLabel:
    view = QLabel(text)
    font = QFont()
    font.setPointSize(size)
    font.setBold(True)
    view.setFont(font)
    return view


def Heading(text: str) -> QLabel:
    return Title(text, 15)


class Subtitle(QLabel):
    def __init__(self, text: str = "") -> None:
        super().__init__(text)
        font = QFont()
        font.setPointSize(14)
        self.setFont(font)
        self.update_color()

    def update_color(self) -> None:
        palette = QApplication.palette()
        text = palette.color(QPalette.ColorRole.WindowText)
        window = palette.color(QPalette.ColorRole.Window)
        secondary = QColor(
            (3 * text.red() + 2 * window.red()) // 5,
            (3 * text.green() + 2 * window.green()) // 5,
            (3 * text.blue() + 2 * window.blue()) // 5,
        )
        palette.setColor(QPalette.ColorRole.WindowText, secondary)
        palette.setColor(QPalette.ColorRole.Text, secondary)
        self.setPalette(palette)

    def changeEvent(self, event: Optional[QEvent]) -> None:
        super().changeEvent(event)
        if event is not None and event.type() == QEvent.Type.ApplicationPaletteChange:
            self.update_color()


class ClickLabel(QLabel):
    clicked = pyqtSignal()

    def mouseReleaseEvent(self, event: Optional[QMouseEvent]) -> None:
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class CoreTableModel(QAbstractTableModel):
    header_names: list[str] = []
    align: list[str] = []
    not_editable: list[int] = []
    placeholders: dict[int, str] = {}

    def __init__(self, parent: Optional[QWidget], content: list[Any]) -> None:
        super().__init__(parent)
        self.content = content
        self.ncols = len(self.header_names)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.content)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return self.ncols

    def get_data(self, row: int, col: int) -> Any:
        return None

    def deep_data(self, row: int, col: int, is_display: bool) -> Any:
        return self.get_data(row, col)

    def alignment(self, col: int) -> Qt.AlignmentFlag:
        align = self.align[col] if col < len(self.align) else ""
        if align == "right":
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        elif align == "left":
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        else:
            return Qt.AlignmentFlag.AlignCenter

    def is_placeholder(self, row: int, col: int) -> bool:
        return col in self.placeholders and self.deep_data(row, col, True) == ""

    def sort_key(self, row: int, col: int) -> tuple[int, float, str]:
        value = self.deep_data(row, col, False)
        text = "" if value is None else str(value)
        try:
            number = float(text)
        except ValueError:
            return (1, 0, text.lower())
        if not math.isfinite(number):
            return (1, 0, text.lower())
        return (0, number, "")

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not (
            0 <= index.row() < len(self.content) and 0 <= index.column() < self.ncols
        ):
            return None
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self.alignment(index.column())
        if role == Qt.ItemDataRole.ForegroundRole and self.is_placeholder(
            index.row(), index.column()
        ):
            return QApplication.palette().color(QPalette.ColorRole.PlaceholderText)
        if role == Qt.ItemDataRole.DisplayRole and self.is_placeholder(
            index.row(), index.column()
        ):
            return self.placeholders[index.column()]
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self.deep_data(
                index.row(), index.column(), role == Qt.ItemDataRole.DisplayRole
            )

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal or not 0 <= section < self.ncols:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return self.header_names[section]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return self.alignment(section)
        return None

    def set_data(self, row: int, col: int, value: Any) -> bool:
        return True

    def update_col(self, col: int) -> None:
        if not self.content or not 0 <= col < self.ncols:
            return
        index0 = self.index(0, col)
        index1 = self.index(len(self.content) - 1, col)
        self.dataChanged.emit(index0, index1)

    def source_index(self, index: QModelIndex) -> QModelIndex:
        return index

    def table_index(self, index: QModelIndex) -> QModelIndex:
        return index

    def setData(
        self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if (
            not index.isValid()
            or role != Qt.ItemDataRole.EditRole
            or not 0 <= index.row() < len(self.content)
            or not 0 <= index.column() < self.ncols
        ):
            return False
        changed = self.set_data(index.row(), index.column(), value)
        if not changed:
            return False
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        if index.column() in self.not_editable:
            return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def new_entry(self) -> None:
        return None

    def general_new_row(self) -> None:
        self.beginResetModel()
        try:
            self.new_entry()
        finally:
            self.endResetModel()

    def delete_entry(self, row: int) -> None:
        return None

    def general_delete_row(self, index: QModelIndex) -> None:
        index = self.source_index(index)
        if not index.isValid() or not 0 <= index.row() < len(self.content):
            return
        self.beginResetModel()
        try:
            self.delete_entry(index.row())
        finally:
            self.endResetModel()


class CoreTable(QWidget):
    ModelClass: type[CoreTableModel] = CoreTableModel
    item_name: Optional[str] = ""
    default_widths: list[tuple[int, int]] = []
    fixed_widths: list[int] = []
    stretch_widths: list[int] = []
    fit_widths: list[int] = []
    empty_message: Optional[str] = None

    def __init__(self, content: Any) -> None:
        super().__init__()
        self.table = QTableView()
        self.model = self.ModelClass(self.table, content)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        cast(QHeaderView, self.table.verticalHeader()).setVisible(False)
        cast(QHeaderView, self.table.horizontalHeader()).setHighlightSections(False)
        self.resize_columns(
            self.default_widths, self.fixed_widths, self.stretch_widths, self.fit_widths
        )

        self.vbox = QVBoxLayout()
        no_margin(self.vbox)
        self.vbox.setSpacing(10)
        self.vbox.addWidget(self.table)

        self.selection_buttons: list[QPushButton] = []
        if self.item_name != None:
            self.table.customContextMenuRequested.connect(self.open_menu)
            add_button = QPushButton(f"New {self.item_name}")
            add_button.clicked.connect(lambda: self.model.general_new_row())
            remove_button = QPushButton(f"Remove {self.item_name}")
            remove_button.clicked.connect(self.remove_selected)
            self.selection_buttons.append(remove_button)

            self.control_bar_widget = QWidget()
            self.control_bar = QHBoxLayout(self.control_bar_widget)
            no_margin(self.control_bar)
            self.control_bar.setSpacing(4)
            self.control_bar.addWidget(add_button)
            self.control_bar.addWidget(remove_button)
            self.control_bar.addStretch()

            self.vbox.addWidget(self.control_bar_widget)
            for key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                shortcut = QShortcut(QKeySequence(key), self.table)
                shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
                shortcut.activated.connect(self.remove_selected)
            self.model.modelReset.connect(self.update_buttons)
            self.is_editable = True
        else:
            self.is_editable = False

        self.setLayout(self.vbox)
        self.watch_selection()

        if self.empty_message is not None:
            self.empty_label = Subtitle(self.empty_message)
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setWordWrap(True)
            self.empty_label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents
            )
            QVBoxLayout(cast(QWidget, self.table.viewport())).addWidget(
                self.empty_label
            )
            self.model.modelReset.connect(self.update_empty_message)
            self.model.rowsInserted.connect(lambda *args: self.update_empty_message())
            self.model.rowsRemoved.connect(lambda *args: self.update_empty_message())
            self.update_empty_message()

    def update_empty_message(self) -> None:
        self.empty_label.setVisible(self.model.rowCount() == 0)

    def watch_selection(self) -> None:
        cast(QItemSelectionModel, self.table.selectionModel()).selectionChanged.connect(
            self.update_buttons
        )
        self.update_buttons()

    def update_buttons(self) -> None:
        row_selected = cast(
            QItemSelectionModel, self.table.selectionModel()
        ).hasSelection()
        for button in self.selection_buttons:
            button.setEnabled(row_selected)

    def deselect_unless_clicked(self, widget: QWidget, position: QPoint) -> None:
        if widget is self.table.viewport():
            if self.table.indexAt(position).isValid():
                return
        elif (
            widget is self.table
            or self.table.isAncestorOf(widget)
            or widget in self.selection_buttons
        ):
            return
        self.table.clearSelection()

    def remove_selected(self) -> None:
        index = self.table.currentIndex()
        selection = cast(QItemSelectionModel, self.table.selectionModel())
        if not (
            self.is_editable
            and index.isValid()
            and selection.isRowSelected(index.row(), QModelIndex())
        ):
            return
        item = self.model.content[self.model.source_index(index).row()]
        self.model.general_delete_row(index)
        rows = [row for row, entry in enumerate(self.model.content) if entry is item]
        if rows:
            self.table.selectRow(
                self.model.table_index(self.model.index(rows[0], 0)).row()
            )

    def resize_columns(
        self,
        default_widths: list[tuple[int, int]],
        fixed_widths: list[int],
        stretch_widths: list[int],
        fit_widths: list[int],
    ) -> None:
        header = cast(QHeaderView, self.table.horizontalHeader())
        for row, width in default_widths:
            self.table.setColumnWidth(row, width)
        for row in fixed_widths:
            header.setSectionResizeMode(row, QHeaderView.ResizeMode.Fixed)
        for row in stretch_widths:
            header.setSectionResizeMode(row, QHeaderView.ResizeMode.Stretch)
        for row in fit_widths:
            header.setSectionResizeMode(row, QHeaderView.ResizeMode.ResizeToContents)

    def open_menu(self, position: QPoint) -> None:
        if not self.is_editable:
            return None

        menu = QMenu()
        index = self.table.indexAt(position)

        if index.isValid():
            remove_action = cast(QAction, menu.addAction(f"Remove {self.item_name}"))
            remove_action.triggered.connect(
                lambda: self.model.general_delete_row(index)
            )
            menu.addSeparator()

        new_transaction = cast(QAction, menu.addAction(f"New {self.item_name}"))
        new_transaction.triggered.connect(lambda: self.model.general_new_row())

        menu.exec(cast(QWidget, self.table.viewport()).mapToGlobal(position))

    def set_editable(self, edit: bool) -> None:
        if self.item_name == None:
            return
        self.is_editable = edit
        if edit:
            self.table.setEditTriggers(
                QTableView.EditTrigger.DoubleClicked
                | QTableView.EditTrigger.EditKeyPressed
            )
        else:
            self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.control_bar_widget.setVisible(edit)


class SelectionClearer(QObject):
    def eventFilter(self, watched: Optional[QObject], event: Optional[QEvent]) -> bool:
        if (
            isinstance(watched, QWidget)
            and isinstance(event, QMouseEvent)
            and event.type() == QEvent.Type.MouseButtonPress
            and watched.childAt(event.position().toPoint()) is None
        ):
            for table in cast(QWidget, watched.window()).findChildren(CoreTable):
                table.deselect_unless_clicked(watched, event.position().toPoint())
        return False


class SortProxy(QSortFilterProxyModel):
    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        model = cast(CoreTableModel, self.sourceModel())
        return model.sort_key(left.row(), left.column()) < model.sort_key(
            right.row(), right.column()
        )


class SortTableModel(CoreTableModel):
    def __init__(self, parent: Optional[QWidget], content: list[Any]) -> None:
        super().__init__(parent, content)
        self.proxy: Optional[QSortFilterProxyModel] = None

    def table_index(self, index: QModelIndex) -> QModelIndex:
        if self.proxy != None:
            return self.proxy.mapFromSource(index)
        else:
            return index

    def source_index(self, index: QModelIndex) -> QModelIndex:
        if self.proxy != None:
            return self.proxy.mapToSource(index)
        else:
            return index

    def set_proxy(self, proxy: QSortFilterProxyModel) -> None:
        self.proxy = proxy


class SortTable(CoreTable):
    model: SortTableModel
    ModelClass: type[CoreTableModel] = SortTableModel

    def __init__(self, content: Any) -> None:
        super().__init__(content)
        sort_model = SortProxy(self.table)
        sort_model.setSourceModel(self.model)
        sort_model.setDynamicSortFilter(True)
        sort_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        sort_model.setFilterKeyColumn(-1)
        self.model.set_proxy(sort_model)

        search_box = QLineEdit()
        search_box.setPlaceholderText(f"Search {self.item_name}s")
        search_box.setClearButtonEnabled(True)
        search_box.textChanged.connect(sort_model.setFilterFixedString)
        self.vbox.insertWidget(0, search_box)

        self.table.setModel(sort_model)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.watch_selection()


class ButtonDelegate(QStyledItemDelegate):
    clicked = pyqtSignal(QModelIndex)
    text = "Open"

    def button_size(self, font_metrics: QFontMetrics) -> QSize:
        button = QStyleOptionButton()
        button.text = self.text
        button.fontMetrics = font_metrics
        return cast(QStyle, QApplication.style()).sizeFromContents(
            QStyle.ContentsType.CT_PushButton, button, font_metrics.size(0, self.text)
        )

    def button(self, option: QStyleOptionViewItem) -> QStyleOptionButton:
        button = QStyleOptionButton()
        button.text = self.text
        button.fontMetrics = option.fontMetrics
        button.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Raised
        size = self.button_size(option.fontMetrics)
        button.rect = QRect(QPoint(0, 0), size.boundedTo(option.rect.size()))
        button.rect.moveCenter(option.rect.center())
        return button

    def paint(
        self,
        painter: Optional[QPainter],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        if painter is None:
            return
        super().paint(painter, option, index)
        cast(QStyle, QApplication.style()).drawControl(
            QStyle.ControlElement.CE_PushButton, self.button(option), painter
        )

    def editorEvent(
        self,
        event: Optional[QEvent],
        model: Optional[QAbstractItemModel],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> bool:
        if (
            isinstance(event, QMouseEvent)
            and event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
            and self.button(option).rect.contains(event.position().toPoint())
        ):
            self.clicked.emit(index)
            return True
        return False


class ChoiceDelegate(QStyledItemDelegate):
    def __init__(
        self, parent: Optional[QWidget], choices: Callable[[], dict[str, str]]
    ) -> None:
        super().__init__(parent)
        self.choices = choices

    def createEditor(
        self,
        parent: Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> QWidget:
        editor = QComboBox(parent)
        editor.setAutoFillBackground(True)
        for label, value in sorted(
            self.choices().items(), key=lambda choice: choice[0].lower()
        ):
            editor.addItem(label, value)
        return editor

    def setEditorData(self, editor: Optional[QWidget], index: QModelIndex) -> None:
        combo = cast(QComboBox, editor)
        combo.setCurrentIndex(combo.findData(index.data(Qt.ItemDataRole.EditRole)))

    def setModelData(
        self,
        editor: Optional[QWidget],
        model: Optional[QAbstractItemModel],
        index: QModelIndex,
    ) -> None:
        if model is not None:
            model.setData(
                index, cast(QComboBox, editor).currentData(), Qt.ItemDataRole.EditRole
            )


class TextDelegate(QStyledItemDelegate):
    padding = 6

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        size = super().sizeHint(option, index)
        view = self.parent()
        row = (
            cast(QHeaderView, view.verticalHeader()).defaultSectionSize()
            if isinstance(view, QTableView)
            else 0
        )
        single_line = size.height() < 2 * option.fontMetrics.lineSpacing()
        height = row if single_line else size.height() + 2 * self.padding
        return QSize(size.width(), height)

    def createEditor(
        self,
        parent: Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> QWidget:
        editor = QPlainTextEdit(parent)
        editor.setTabChangesFocus(True)
        cast(QTextDocument, editor.document()).setDocumentMargin(self.padding)
        return editor

    def setEditorData(self, editor: Optional[QWidget], index: QModelIndex) -> None:
        text_editor = cast(QPlainTextEdit, editor)
        text_editor.setPlainText(index.data(Qt.ItemDataRole.EditRole) or "")
        text_editor.moveCursor(QTextCursor.MoveOperation.End)

    def setModelData(
        self,
        editor: Optional[QWidget],
        model: Optional[QAbstractItemModel],
        index: QModelIndex,
    ) -> None:
        if model is not None:
            model.setData(
                index,
                cast(QPlainTextEdit, editor).toPlainText(),
                Qt.ItemDataRole.EditRole,
            )

    def updateEditorGeometry(
        self,
        editor: Optional[QWidget],
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        if editor is None:
            return
        rect = QRect(option.rect)
        line = option.fontMetrics.lineSpacing()
        rect.setHeight(max(rect.height() + 2 * line, 5 * line))
        viewport = editor.parentWidget()
        if viewport is not None and rect.bottom() >= viewport.height():
            rect.moveTop(max(0, viewport.height() - rect.height()))
        editor.setGeometry(rect)

    def eventFilter(self, object: Optional[QObject], event: Optional[QEvent]) -> bool:
        if (
            isinstance(object, QPlainTextEdit)
            and isinstance(event, QKeyEvent)
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.commitData.emit(object)
            self.closeEditor.emit(object)
            return True
        return super().eventFilter(object, event)


class ServingsBox(QDoubleSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setLocale(QLocale.c())
        self.setDecimals(2)
        self.setRange(0.01, 999)
        self.setValue(1)

    def textFromValue(self, value: float) -> str:
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def servings(self) -> Decimal:
        return Decimal(self.textFromValue(self.value()))


class DashboardTableModel(SortTableModel):
    def action(self, index: QModelIndex) -> None:
        index = self.source_index(index)
        if not index.isValid() or not 0 <= index.row() < len(self.content):
            return
        self.content[index.row()].get_window()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            if index.column() == self.ncols - 1:
                return ""

        return super().data(index, role)


class DashboardTable(SortTable):
    model: DashboardTableModel

    def __init__(self, content: Any) -> None:
        super().__init__(content)
        delegate = ButtonDelegate(self.table)
        self.table.setItemDelegateForColumn(self.model.ncols - 1, delegate)
        delegate.clicked.connect(self.model.action)
        self.table.activated.connect(self.model.action)
        button_size = delegate.button_size(self.table.fontMetrics())
        rows = cast(QHeaderView, self.table.verticalHeader())
        rows.setDefaultSectionSize(
            max(rows.defaultSectionSize(), button_size.height() + 2)
        )
        self.resize_columns(
            [(self.model.ncols - 1, button_size.width() + 16)],
            [self.model.ncols - 1],
            [],
            [],
        )


class FixTable(CoreTable):
    def __init__(self, content: Any) -> None:
        self.up_button = symbol_button("↑", f"Move the selected {self.item_name} up")
        self.down_button = symbol_button(
            "↓", f"Move the selected {self.item_name} down"
        )
        super().__init__(content)

        self.up_button.clicked.connect(lambda: self.move_row(-1))
        self.down_button.clicked.connect(lambda: self.move_row(1))
        self.control_bar.addWidget(self.up_button)
        self.control_bar.addWidget(self.down_button)
        self.selection_buttons += [self.up_button, self.down_button]
        self.update_buttons()

    def update_buttons(self) -> None:
        super().update_buttons()
        row = self.table.currentIndex().row()
        selected = cast(QItemSelectionModel, self.table.selectionModel()).hasSelection()
        self.up_button.setEnabled(selected and row > 0)
        self.down_button.setEnabled(selected and 0 <= row < self.model.rowCount() - 1)

    def move_row(self, offset: int) -> None:
        index = self.table.currentIndex()
        row = index.row()
        target = row + offset
        content = self.model.content
        if not (
            index.isValid() and 0 <= row < len(content) and 0 <= target < len(content)
        ):
            return
        destination = target + 1 if offset > 0 else target
        if not self.model.beginMoveRows(
            QModelIndex(), row, row, QModelIndex(), destination
        ):
            return
        content[row], content[target] = content[target], content[row]
        self.model.endMoveRows()
        self.table.selectRow(target)
        self.update_buttons()


class EntriesModel(CoreTableModel):
    content: list[list[Any]]
    align = ["left", "right"]
    refresh = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QWidget],
        content: tuple[Union[Recipe, Mealplan], list[list[Any]], str],
    ) -> None:
        self.owner, entries, self.item_name = content
        self.cookbook = self.owner.cookbook
        self.header_names = [self.item_name.capitalize(), "Amount"]
        self.servings = Decimal(1)
        super().__init__(parent, entries)

    def set_servings(self, servings: Decimal) -> None:
        self.servings = servings
        self.update_col(1)

    def deep_data(self, row: int, col: int, is_display: bool) -> Optional[str]:
        component: Union[Ingredient, Recipe] = self.content[row][0]
        amount: Decimal = self.content[row][1]
        if col == 0:
            if is_display:
                return component.display_name()
            else:
                return component._id
        elif col == 1:
            if is_display:
                return amount_string(
                    exact_string(amount * self.servings), component.unit
                )
            else:
                return str(amount)
        return None

    def set_data(self, row: int, col: int, value: Any) -> bool:
        if col == 0:
            changed = self.cookbook.change_entry(
                self.owner, self.content, row, component_id=value
            )
        elif col == 1:
            changed = self.cookbook.change_entry(
                self.owner, self.content, row, amount=value
            )
        else:
            return False
        if changed:
            self.refresh.emit()
        return changed

    def choices(self) -> dict[str, str]:
        return component_choices(
            c for c in self.cookbook._components.values() if c is not self.owner
        )

    def new_entry(self) -> None:
        parent = cast(Optional[QWidget], self.parent())
        new_id = ask_choice(
            parent,
            f"New {self.item_name}",
            "Choose an ingredient or recipe:",
            self.choices(),
        )
        if new_id is not None and not self.cookbook.add_entry(
            self.owner, self.content, new_id
        ):
            name = self.cookbook._components[new_id].display_name()
            show_error(
                parent, f"Could not add '{name}', because it contains this recipe."
            )

    def delete_entry(self, row: int) -> None:
        self.cookbook.remove_entry(self.owner, self.content, row)


class EntriesTable(FixTable):
    model: EntriesModel
    ModelClass = EntriesModel
    item_name: str = ""
    default_widths = [(1, 130)]
    fixed_widths = [1]
    stretch_widths = [0]

    def __init__(
        self, owner: Union[Recipe, Mealplan], entries: list[list[Any]]
    ) -> None:
        super().__init__((owner, entries, self.item_name))
        self.table.setItemDelegateForColumn(
            0, ChoiceDelegate(self.table, self.model.choices)
        )


class DetailView(QWidget):
    metric_suffix = ""

    def __init__(
        self,
        item: Union[Recipe, Mealplan],
        parent: Optional[QWidget],
        width: int,
        height: int,
    ) -> None:
        super().__init__(parent=parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.resize(width, height)
        self.item = item
        self.editing = False

        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        general_margin(self.vbox)
        self.vbox.setSpacing(15)

        heading = QVBoxLayout()
        no_margin(heading)
        heading.setSpacing(4)
        hbox = QHBoxLayout()
        self.name_label = Title("")
        self.main_metric_label = Title("")
        self.other_metrics_label = Subtitle("")
        hbox.addWidget(self.name_label)
        hbox.addStretch(1)
        hbox.addWidget(self.main_metric_label)
        heading.addLayout(hbox)
        heading.addWidget(self.other_metrics_label)
        self.vbox.addLayout(heading)

        self.body = QVBoxLayout()
        no_margin(self.body)
        self.body.setSpacing(15)
        self.vbox.addLayout(self.body)

        self.controls = QHBoxLayout()
        no_margin(self.controls)
        self.controls.addStretch()
        self.edit_button = QPushButton("Edit")
        self.edit_button.setDefault(True)
        self.edit_button.clicked.connect(self.toggle_edit)
        self.controls.addWidget(self.edit_button)
        self.vbox.addLayout(self.controls)

        self.refresh_name()

    def open(self) -> None:
        self.refresh()
        self.set_editing(False)
        self.show()

    def set_editing(self, edit: bool) -> None:
        self.editing = edit
        self.edit_button.setText("Done" if edit else "Edit")

    def toggle_edit(self) -> None:
        self.set_editing(not self.editing)

    def refresh(self) -> None:
        metrics = metric_strings(self.item.get_metrics(), self.metric_suffix)
        self.main_metric_label.setText(metrics[0] if metrics else "")
        self.other_metrics_label.setText(" · ".join(metrics[1:]))
        self.other_metrics_label.setVisible(len(metrics) > 1)

    def refresh_name(self) -> None:
        self.setWindowTitle(self.item.display_name())
        self.name_label.setText(self.item.display_name())
