from __future__ import annotations
from typing import Optional, cast
import sys, os, signal

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QListWidget,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtGui import QCloseEvent, QShowEvent

from .cookbook import Cookbook
from .ingredient import IngredientTable
from .recipe import RecipeDashTable
from .mealplan import MealplanDashTable
from .metric import MetricTable
from .views import (
    Title,
    Subtitle,
    show_error,
    ask_confirmation,
    general_margin,
    ClickLabel,
    SelectionClearer,
)
from . import __version__

os.environ["QT_LOGGING_RULES"] = "*.warning=false"

settings = QSettings("SGCink", "Kytchen")


def select_file(parent: Optional[QWidget], save: bool) -> Optional[str]:
    if save:
        dialogue = QFileDialog.getSaveFileName
        msg = "Save your cookbook"
    else:
        dialogue = QFileDialog.getOpenFileName
        msg = "Open a cookbook"

    file_path, _ = dialogue(parent, msg, "", "Cookbooks (*.json)")
    if not file_path:
        return None
    if save and not file_path.endswith(".json"):
        file_path = file_path + ".json"
    return file_path


def write_cookbook(cookbook: Cookbook, path: str) -> bool:
    try:
        cookbook.save(path)
    except OSError as error:
        show_error(cookbook.window, f"Could not save {path}: {error}")
        return False
    return True


def safe_save(cookbook: Cookbook, please: bool = False) -> bool:
    if cookbook.is_empty() and not please:
        return True
    path = cookbook.path or select_file(cookbook.window, True)
    if path is None or not write_cookbook(cookbook, path):
        return False
    cookbook.set_path(path)
    settings.setValue("last_file", os.path.abspath(path))
    return True


class HomeView(QWidget):
    def __init__(self, parent: MainWindow, cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(2)

        layout.addWidget(
            Title("Welcome to your Kytchen!"), alignment=Qt.AlignmentFlag.AlignHCenter
        )
        layout.addSpacing(8)

        if cookbook.path == None:
            message = "You are editing a new cookbook. Save it to keep your changes."
        else:
            message = (
                f"You are editing ‘{cookbook.get_name()}’. "
                "It is saved automatically when you close Kytchen."
            )
        status = Subtitle(message)
        status.setWordWrap(True)
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status)
        self.summary = Subtitle("")
        self.summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.summary)
        layout.addSpacing(30)

        button_bar = QHBoxLayout()
        button_bar.addStretch()
        if cookbook.path == None:
            save_button = QPushButton("Save")
            save_button.setDefault(True)
            save_button.clicked.connect(parent.save_update)
            button_bar.addWidget(save_button)
        save_as_button = QPushButton("Save as…")
        save_as_button.clicked.connect(self.save_as)
        open_button = QPushButton("Open another cookbook…")
        open_button.clicked.connect(parent.open_cookbook)
        new_button = QPushButton("New cookbook")
        new_button.clicked.connect(parent.new_cookbook)
        close_button = QPushButton("Close without saving")
        close_button.clicked.connect(parent.close_without_saving)
        for button in [save_as_button, open_button, new_button, close_button]:
            button_bar.addWidget(button)
        button_bar.addStretch()
        layout.addLayout(button_bar)
        layout.addStretch(3)
        self.refresh()

    def refresh(self) -> None:
        counts = [
            (len(self.cookbook.ingredients), "ingredient"),
            (len(self.cookbook.recipes), "recipe"),
            (len(self.cookbook.mealplans), "meal plan"),
        ]
        self.summary.setText(
            " · ".join(
                f"{count} {name}{'' if count == 1 else 's'}" for count, name in counts
            )
        )

    def showEvent(self, event: Optional[QShowEvent]) -> None:
        self.refresh()
        super().showEvent(event)

    def save_as(self) -> None:
        path = select_file(self, True)
        if path is not None:
            write_cookbook(self.cookbook, path)


class AboutWindow(QWidget):
    def __init__(self, parent: Optional[QWidget]) -> None:
        super().__init__(parent=parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowTitle("About Kytchen")
        self.setFixedSize(400, 300)
        self.vbox = QVBoxLayout()
        self.setLayout(self.vbox)
        general_margin(self.vbox)
        self.vbox.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        name = Title("Kytchen")
        version = Subtitle(f"Version {__version__}")
        desc = QLabel('<a href="https://kytchen.sgc.ink">kytchen.sgc.ink</a>')
        desc.setOpenExternalLinks(True)
        license0 = QLabel(
            "Copyright © Samuel González-Castillo\n\
This program is distributed under the MIT license"
        )
        license0.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.vbox.addStretch()
        for widget in [name, version, desc]:
            self.vbox.addWidget(widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.vbox.addSpacing(20)
        self.vbox.addWidget(license0, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.vbox.addStretch()


SIDEBAR_STYLE = """
QWidget#sidebar {
    background: #9C4900;
}
QLabel#brand {
    color: white;
    font-size: 20pt;
    font-weight: bold;
    padding: 0 10px 16px 10px;
}
QListWidget {
    background: transparent;
    border: none;
    outline: 0;
    font-size: 13pt;
}
QListWidget::item, ClickLabel {
    color: white;
    font-size: 13pt;
    padding: 7px 10px;
    border: none;
    border-radius: 6px;
}
QListWidget::item:hover, ClickLabel:hover {
    background-color: rgba(255, 255, 255, 40);
}
QListWidget::item:selected {
    background-color: white;
    color: #A64D00;
}
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.save_on_close = True
        self.about = AboutWindow(self)
        self.setGeometry(200, 200, 1000, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        SIDEBAR_MARGIN = 20

        self.stack = QStackedWidget()
        self.stack.setContentsMargins(20, 20, 20, 20)
        main_layout = QHBoxLayout(central_widget)
        sidebar_container = QWidget()
        sidebar_container.setObjectName("sidebar")
        sidebar_container.setFixedWidth(160)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setSpacing(0)
        main_layout.addWidget(sidebar_container)
        main_layout.addWidget(self.stack)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        sidebar_layout.setContentsMargins(10, SIDEBAR_MARGIN, 10, SIDEBAR_MARGIN)

        brand = QLabel("Kytchen")
        brand.setObjectName("brand")
        sidebar_layout.addWidget(brand)

        sidebar = QListWidget()
        sidebar.addItems(["Home", "Ingredients", "Recipes", "Meal plans", "Metrics"])
        sidebar.setSpacing(2)
        sidebar.currentRowChanged.connect(self.menu_action)
        sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar = sidebar

        sidebar_layout.addWidget(sidebar)
        view_about = ClickLabel("About")
        view_about.setCursor(Qt.CursorShape.PointingHandCursor)
        view_about.clicked.connect(self.show_about)
        sidebar_layout.addWidget(view_about)

        sidebar_container.setStyleSheet(SIDEBAR_STYLE)

        last_file = settings.value("last_file", None)

        cookbook = Cookbook()
        if last_file != None:
            try:
                cookbook = Cookbook.load(last_file)
            except Exception as error:
                message = (
                    f"Could not load {last_file}.\n\n{type(error).__name__}: {error}"
                )
                QTimer.singleShot(0, lambda: show_error(self, message))
        self.set_cookbook(cookbook)

    def menu_action(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def set_cookbook(self, cookbook: Cookbook) -> None:
        while self.stack.count() > 0:
            widget = cast(QWidget, self.stack.widget(0))
            self.stack.removeWidget(widget)
            widget.deleteLater()
        self.setWindowTitle(f"Kytchen — {cookbook.get_name()}")
        self.cookbook = cookbook
        metric_table = MetricTable(cookbook)
        metric_table.model.changed.connect(self.refresh_metrics)
        self.views = [HomeView(self, cookbook), *self.metric_views(), metric_table]
        for view in self.views:
            self.stack.addWidget(view)
        self.cookbook.window = self
        self.sidebar.setCurrentRow(0)

    def metric_views(self) -> list[QWidget]:
        return [
            IngredientTable(self.cookbook),
            RecipeDashTable(self.cookbook),
            MealplanDashTable(self.cookbook),
        ]

    def refresh_metrics(self) -> None:
        for index, view in enumerate(self.metric_views(), start=1):
            old = self.views[index]
            self.views[index] = view
            self.stack.insertWidget(index, view)
            self.stack.removeWidget(old)
            old.deleteLater()
        for recipe in self.cookbook.recipes:
            if recipe.window != None:
                recipe.window.refresh()
        for mealplan in self.cookbook.mealplans:
            if mealplan.window != None:
                mealplan.window.refresh()

    def save_update(self) -> None:
        if safe_save(self.cookbook, please=True):
            self.set_cookbook(self.cookbook)

    def new_cookbook(self) -> None:
        if not safe_save(self.cookbook):
            return
        self.set_cookbook(Cookbook())

    def open_cookbook(self) -> bool:
        if not safe_save(self.cookbook):
            return False
        path = select_file(self, False)
        if path is None:
            return False
        try:
            new_cookbook = Cookbook.load(path)
        except:
            show_error(self, f"Could not load {path}.")
            return False
        self.set_cookbook(new_cookbook)
        return True

    def closeEvent(self, event: Optional[QCloseEvent]) -> None:
        # TODO: Ask user if they want to save changes before closing
        if event is None:
            return
        if self.save_on_close and not safe_save(self.cookbook):
            event.ignore()
            return
        event.accept()

    def close_without_saving(self) -> None:
        if ask_confirmation(
            self,
            "Close Kytchen without saving? Changes made since the cookbook "
            "was last saved will be lost.",
            "Close without saving",
        ):
            self.save_on_close = False
            self.close()

    def show_about(self) -> None:
        self.about.show()


def main() -> None:
    app = QApplication(sys.argv)
    app.installEventFilter(SelectionClearer(app))
    window = MainWindow()
    window.show()
    signal.signal(signal.SIGINT, lambda *args: app.closeAllWindows())
    interrupt_check = QTimer()
    interrupt_check.timeout.connect(lambda: None)
    interrupt_check.start(200)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
