import sys, os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QStackedWidget, QListWidget, QFileDialog,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QIcon, QPixmap

from .cookbook import Cookbook
from .ingredient import IngredientTable
from .recipe import RecipeDashTable
from .mealplan import MealplanDashTable
from .views import Title, Subtitle, show_error, general_margin, ClickLabel
from . import __version__

os.environ["QT_LOGGING_RULES"] = "*.warning=false"

settings = QSettings("SGCink", "Kytchen")

#BASEDIR = Path(__file__).parent
#ICON_PATH = str(BASEDIR / "kytchen.png")

def select_file(parent, save):
    if save:
        dialogue = QFileDialog.getSaveFileName
        msg = "Save your cookbook"
    else:
        dialogue = QFileDialog.getOpenFileName
        msg = "Open a cookbook"
    
    file_path, ok = dialogue(parent, msg, "", "Cookbooks (*.js)")
    if ok and save and not file_path.endswith(".js"):
        file_path = file_path + ".js"
    return file_path, ok

def safe_save(cookbook, please = False):
    if cookbook.is_empty() and not please:
        return
    while not cookbook.path:
        path, ok = select_file(cookbook.window, True)
        if not ok:
            return
        cookbook.set_path(path)
    cookbook.save()
    settings.setValue("last_file", os.path.abspath(cookbook.path))

class HomeView(QWidget):
    def __init__(self, parent, cookbook):
        self.cookbook = cookbook
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        layout.addWidget(Title("Welcome to your Kytchen!"),
                         alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(5)

        if cookbook.path == None:
            layout.addWidget(Subtitle("You are editing a new cookbook."),
                             alignment=Qt.AlignmentFlag.AlignHCenter)
            layout.addSpacing(10)
            save_button = QPushButton("Save")
            save_button.setMinimumHeight(40)
            save_button.clicked.connect(parent.save_update)
            layout.addWidget(save_button)
        else:
            layout.addWidget(Subtitle(
                f"You are editing the '{cookbook.get_name()}'. \
It will be saved automatically."
            ), alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(100)

        button_bar = QHBoxLayout() 
        save_as_button = QPushButton("Save as...")
        save_as_button.setMinimumHeight(50)
        save_as_button.clicked.connect(self.save_as)
        open_button = QPushButton("Open another cookbook")
        open_button.clicked.connect(parent.open_cookbook)
        new_button = QPushButton("New cookbook")
        new_button.clicked.connect(parent.new_cookbook)
        for button in [save_as_button, open_button, new_button]:
            button.setMinimumHeight(40)
            button_bar.addWidget(button)
        layout.addLayout(button_bar)

        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setContentsMargins(40,70,40,70)

    def save_as(self):
        path = None
        while not path:
            path, ok = select_file(self, True)
            if not ok:
                return
        self.cookbook.save(path)

class AboutWindow(QWidget):
    def __init__(self, parent):
        super().__init__(parent = parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.setWindowTitle("About Kytchen")
        self.setFixedSize(400,300)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        general_margin(self.layout)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        #logo_img = QPixmap(ICON_PATH)
        #logo = QLabel()
        #logo.setFixedSize(85, 85)
        #logo.setPixmap(logo_img)
        #logo.setScaledContents(True)

        name = Title(f"Kytchen {__version__}")
        desc = Subtitle('<a href="https://kytchen.sgc.ink">kytchen.sgc.ink</a>')
        desc.setOpenExternalLinks(True)
        license0 = QLabel("Copyright © Samuel González-Castillo\n\
This program is distributed under the MIT license")
        license0.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # TODO Add logo
        for widget in [name, desc, license0]:
            self.layout.addWidget(widget,
                                  alignment=Qt.AlignmentFlag.AlignHCenter)

SIDEBAR_STYLE = """
QWidget{
    background: #c66305;
    font-size:11pt;
}
QListWidget {
    background: transparent;
    border: none;
}
QListWidget::item, ClickLabel {
    background-color: #934a04;
    color: white;
    padding: 10px;
    border: none;
    margin: 0;
}
QListWidget:item:hover, ClickLabel:hover {
    background-color: #c88546; 
}
QListWidget::item:selected {
    background-color: #000;
    outline: 0;
    border: none;
}
"""

class MainWindow(QMainWindow):
    def __init__(self, cookbook):
        super().__init__()
        self.about = AboutWindow(self)
        self.setGeometry(200, 200, 1000, 700)
        self.cookbook = None
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
    
        SIDEBAR_MARGIN = 20

        self.stack = QStackedWidget()
        main_layout = QHBoxLayout(central_widget)
        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(120)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setSpacing(0)
        main_layout.addWidget(sidebar_container)
        main_layout.addWidget(self.stack)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        sidebar_layout.setContentsMargins(0,SIDEBAR_MARGIN,0,SIDEBAR_MARGIN)

        sidebar = QListWidget()
        sidebar.addItems(["Home", "Ingredients", "Recipes", "Meal plans"])
        sidebar.currentRowChanged.connect(self.menu_action)
        sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar = sidebar
        
        sidebar_layout.addWidget(sidebar)
        view_about = ClickLabel("About")
        view_about.clicked.connect(self.show_about)
        sidebar_layout.addWidget(view_about)

        sidebar_container.setStyleSheet(SIDEBAR_STYLE)

        last_file = settings.value("last_file", None)
        if last_file != None:
            try:
                cookbook = Cookbook.load(last_file)
            except:
                pass
        self.set_cookbook(cookbook)

    def menu_action(self, index):
        self.stack.setCurrentIndex(index)

    def set_cookbook(self, cookbook):
        if self.cookbook != None:
            while self.stack.count() > 0:
                widget = self.stack.widget(0)
                self.stack.removeWidget(widget)
                widget.deleteLater()
        self.setWindowTitle(f"Kytchen - {cookbook.get_name()}")
        self.cookbook = cookbook
        self.views = [
            HomeView(self, cookbook),
            IngredientTable(cookbook),
            RecipeDashTable(cookbook),
            MealplanDashTable(cookbook)
        ]
        for view in self.views:
            self.stack.addWidget(view)
        self.cookbook.window = self
        self.sidebar.setCurrentRow(0)

    def save_update(self):
        safe_save(self.cookbook, please = True)
        self.set_cookbook(self.cookbook)

    def new_cookbook(self):
        safe_save(self.cookbook)
        self.set_cookbook(Cookbook())
    
    def open_cookbook(self):
        safe_save(self.cookbook)
        path, ok = select_file(self, False)
        if not ok:
            return False
        try:
            new_cookbook = Cookbook.load(path)
        except:
            show_error(self, f"Could not load {path}.")
            return False
        self.set_cookbook(new_cookbook)
        return True

    def closeEvent(self, event):
        safe_save(self.cookbook)
        event.accept()

    def show_about(self):
        self.about.show()

def main():
    app = QApplication(sys.argv)
    #app.setWindowIcon(QIcon(ICON_PATH))
    cb = Cookbook()
    window = MainWindow(cb)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

