from __future__ import annotations
from typing import Callable, Optional, cast

from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QObject,
    QModelIndex,
    QEvent,
    QAbstractItemModel,
    QPoint,
    QRect,
    QSize,
)
from PyQt6.QtWidgets import (
    QTableView,
    QHeaderView,
    QWidget,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionButton,
    QApplication,
    QStyleOptionViewItem,
    QComboBox,
    QPlainTextEdit,
)
from PyQt6.QtGui import (
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QTextCursor,
    QTextDocument,
)


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
