from __future__ import annotations
from typing import TYPE_CHECKING, Any, Iterable, Optional, Union

if TYPE_CHECKING:
    from .mealplan import Mealplan
    from .recipe import Recipe

from PyQt6.QtCore import Qt, pyqtSignal, QLocale, QEvent
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QApplication,
    QMessageBox,
    QInputDialog,
    QLabel,
    QLayout,
    QDoubleSpinBox,
)
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPalette
from decimal import Decimal
from .numeric import metric_strings


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
