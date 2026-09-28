from typing import TYPE_CHECKING, Any, Optional, Union, cast

if TYPE_CHECKING:
    from .cookbook import Cookbook
    from .ingredient import Ingredient
    from .recipe import Recipe

import math
from decimal import Decimal

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QInputDialog, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QListWidget, QStackedWidget
)
from .views import (
    DashboardTable, DashboardTableModel, CoreTableModel,
    FixTable, CoreTable, num, Numeric, Title, no_margin, general_margin
)


class Mealplan:
    def __init__(self, cookbook: Cookbook, name: str = "") -> None:
        self.name = name
        self.cookbook = cookbook 
        self._days: list[list[list[Any]]] = []
        self._shopping_list: dict[Ingredient, Decimal] = {}
        self.window: Optional[MealplanView] = None

    def export(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name}
        days = []
        for day in self._days:
            days.append([ [e[0]._id, str(e[1])] for e in day] )
        data["days"] = days
        return data

    @classmethod
    def load(cls, data: dict[str, Any], cookbook: Cookbook) -> Mealplan:
        self = cls(cookbook, data["name"])
        for day in data["days"]:
            new_day: list[list[Any]] = []
            for entry in day:
                self._new_component(new_day, entry[0], entry[1], strict = True)
            self._days.append(new_day)
        return self

    def new_day(self) -> None:
        self._days.append([])

    def _update_shopping(self, component: Union[Ingredient, Recipe], increase: Decimal = Decimal(0), decrease: Decimal = Decimal(0)) -> None:
        if increase == Decimal(0) and decrease == Decimal(0):
            return
        net = increase - decrease
        changes = component.get_ingredients(net)
        for ingredient, amount in changes.items():
            self._update_ingredient_shopping(ingredient, amount)
        
    def _update_ingredient_shopping(self, ingredient: Ingredient, net: Decimal) -> None:
        self._shopping_list.setdefault(ingredient, Decimal(0))
        self._shopping_list[ingredient] += net
        if self._shopping_list[ingredient] == 0:
            del self._shopping_list[ingredient]

    def _new_component(self, day_list: list[list[Any]], component_id: str, amount: Numeric = Decimal(0), strict: bool = False) -> bool:
        try:
            amount = num(amount)
        except:
            if strict:
                raise ValueError("invalid amount")
            return False
        component = self.cookbook.link_component(self, component_id)
        if component != None:
            day_list.append([component, amount])
            self._update_shopping(component, increase = amount)
            return True
        if strict:
            raise ValueError("invalid component ID")
        return False

    def _remove_component(self, day_list: list[list[Any]], index: int) -> None:
        component, amount = day_list[index]
        self.cookbook.unlink_component(self, component)
        self._update_shopping(component, decrease = amount)
        del day_list[index]

    def _change_amount(self, day_list: list[list[Any]], index: int, new_amount: Numeric, strict: bool = False) -> bool:
        component, old_amount = day_list[index]
        try:
            new_amount = num(new_amount)
        except:
            if strict:
                raise ValueError("invalid amount")
            return False
        self._update_shopping(component, increase = new_amount, decrease = old_amount)
        day_list[index][1] = new_amount
        return True

    def _change_component(self, day_list: list[list[Any]], index: int, new_id: str) -> None:
        old_component, amount = day_list[index]
        new_component = self.cookbook.link_component(self, new_id)
        if new_component == None:
            return
        self.cookbook.unlink_component(self, old_component)
        self._update_shopping(old_component, decrease = amount)
        self._update_shopping(new_component, increase = amount)
        day_list[index][0] = new_component

    def remove_day(self, day: int) -> None:
        ls = self._days[day]
        for i in range(len(ls)):
            self._remove_component(ls, 0)
        del self._days[day]

    def get_shopping_list(self) -> list[list[str]]:
        ls = []
        for component, amount in self._shopping_list.items():
            ls.append([component.name, str(amount)])
        ls.sort(key = lambda entry: entry[0])
        return ls

    def get_calories(self) -> Union[Decimal, int]:
        calories = Decimal(0)
        if len(self._days) == 0:
            return calories
        for element, amount in self._shopping_list.items():
            calories += element.get_calories() * amount
         
        return math.ceil(calories / len(self._days))

    def __str__(self) -> str:
        string = self.name
        string += "\n\n"
        for i, day in enumerate(self._days):
            string += f"DAY {i + 1}"
            for item, amount in day:
                string += f"\n- {item.name} ({amount} {item.unit})"
        string += f"Average daily energy: {self.get_calories()} kcal\n"
        return string

    def __repr__(self) -> str:
        return self.name

    def str_shopping_list(self) -> str:
        string = "";
        ingredients = self._shopping_list
        for ing in ingredients:
            string += f"{ing.name}: {ingredients[ing]} {ing.unit}\n"
        return string

    def get_window(self) -> None:
        if self.window == None:
            self.window = MealplanView(self, self.cookbook.window)
        self.window.set_editing(False)
        self.window.show()

    def _clear(self) -> None:
        if self.window != None:
            self.window.deleteLater()
            self.window = None
        for i in range(len(self._days)):
            self.remove_day(0)

    def _col(self, col: int) -> Optional[str]:
        if col == 0:
            return self.name
        elif col == 1:
            return str(self.get_calories())
        else:
            return None

class MealplanDashModel(DashboardTableModel):
    content: list[Mealplan]
    header_names = ["Meal plan name", "kcal/day", ""]
    align = ["left", "", ""]
    not_editable = [1,2]

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        super().__init__(parent, cookbook.mealplans)

    def get_data(self, row: int, col: int) -> Optional[str]:
        recipe = self.content[row]
        return recipe._col(col)

    def set_data(self, row: int, col: int, value: Any) -> bool:
        mealplan = self.content[row]
        if col == 0:
            mealplan.name = value
            if mealplan.window != None:
                mealplan.window.refresh_name()
        return True       

    def new_entry(self) -> None:
        mealplan = Mealplan(self.cookbook) 
        self.cookbook.register_mealplan(mealplan)
    
    def delete_entry(self, row: int) -> None:
        self.cookbook.delete_mealplan(row) 

 
class MealplanDashTable(DashboardTable):
    ModelClass = MealplanDashModel 
    item_name = "meal plan"
    stretch_widths = [0]

class MealplanView(QWidget):
    def __init__(self, mealplan: Mealplan, parent: Optional[QWidget]) -> None:
        super().__init__(parent = parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.resize(600, 700)
        self.mealplan = mealplan

        self.layout: QVBoxLayout = QVBoxLayout()  # type: ignore[assignment]
        self.setLayout(self.layout)
        no_margin(self.layout)
        self.layout.setSpacing(0)

        name = self.mealplan.name
        if name == "":
            name = "Untitled meal plan"

        hbox = QHBoxLayout()
        general_margin(hbox)
        self.name_label = Title(f"")
        self.kcal_label = Title("")
        hbox.addWidget(self.name_label)
        hbox.addStretch(1)
        hbox.addWidget(self.kcal_label)
        self.layout.addLayout(hbox)

        self.refresh_name()

        self.shopping_view = ShoppingListTable(self.mealplan.get_shopping_list())
        self.main_layout = QHBoxLayout()
        self.layout.addLayout(self.main_layout)
        self.sidebar_container = QVBoxLayout()
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(120)
        self.sidebar_container.addWidget(self.sidebar)
        self.sidebar.currentRowChanged.connect(self.menu_action)
        self.sidebar_buttons_widget = QWidget()
        self.sidebar_buttons = QHBoxLayout(self.sidebar_buttons_widget)
        no_margin(self.sidebar_buttons)
        self.sidebar_buttons.setSpacing(0)
        self.sidebar_container.addWidget(self.sidebar_buttons_widget)
        self.button_add = QPushButton("+")
        self.button_remove = QPushButton("-")
        self.button_add.setMaximumWidth(40)
        self.button_remove.setMaximumWidth(40)
        self.button_add.clicked.connect(self.new_day)
        self.button_remove.clicked.connect(self.remove_day)
        self.sidebar_buttons.addWidget(
            self.button_remove,alignment=Qt.AlignmentFlag.AlignRight)
        self.sidebar_buttons.addWidget(
            self.button_add, alignment=Qt.AlignmentFlag.AlignRight)

        self.stack = QStackedWidget()
        self.main_layout.addLayout(self.sidebar_container)
        self.main_layout.addWidget(self.stack)

        self.sidebar.addItems(["Shopping list"])
        self.stack.addWidget(self.shopping_view)
        self.views: list[MealplanDayTable] = []
        for i in range(len(self.mealplan._days)):
            self.sidebar.addItem(f"Day {i + 1}")
            view = MealplanDayTable(self.mealplan, i)
            self.views.append(view)
            self.stack.addWidget(view)
            view.model.refresh.connect(self.refresh)


        self.controls = QHBoxLayout()
        general_margin(self.controls)
        self.edit_button = QPushButton("")
        self.edit_button.clicked.connect(self.toggle_edit)
        self.set_editing(False)

        self.controls.addStretch()
        self.controls.addWidget(self.edit_button)

        self.layout.addLayout(self.controls)
        self.refresh()

    def menu_action(self, index: int) -> None:
        if index == 0:
            self.shopping_view.model.beginResetModel()
            self.shopping_view.model.content = self.mealplan.get_shopping_list()
            self.shopping_view.model.endResetModel()
        self.stack.setCurrentIndex(index)

    def new_day(self) -> None:
        self.mealplan.new_day()
        day = len(self.mealplan._days)
        self.sidebar.addItem(f"Day {day}")
        view = MealplanDayTable(self.mealplan, day - 1)
        view.set_editable(self.editing)
        self.views.append(view)
        view.model.refresh.connect(self.refresh)
        self.stack.addWidget(view)

    def remove_day(self) -> None:
        if len(self.mealplan._days) == 0:
            return
        last = len(self.mealplan._days) - 1
        label = self.sidebar.takeItem(last + 1)
        del label
        view = self.views.pop()
        self.stack.removeWidget(view)
        view.deleteLater()
        self.mealplan.remove_day(last)

    def set_editing(self, edit: bool) -> None:
        self.editing = edit
        if edit:
            self.edit_button.setText("Save")
        else:
            self.edit_button.setText("Edit")
        for view in self.views:
            view.set_editable(edit)
        self.sidebar_buttons_widget.setVisible(edit)

    def toggle_edit(self) -> None:
        self.set_editing(not self.editing)

    def refresh(self) -> None:
        self.kcal_label.setText(f"{self.mealplan.get_calories()} kcal/day")

    def refresh_name(self) -> None:
        self.setWindowTitle(f"Meal plan '{self.mealplan.name}'")
        self.name_label.setText(self.mealplan.name)

class MealplanDayModel(CoreTableModel):
    content: list[list[Any]]
    header_names = ["Meal", "Amount"]
    align = ["right", ""]
    refresh = pyqtSignal()

    def __init__(self, parent: Optional[QWidget], content: tuple[Mealplan, int]) -> None:
        self.mealplan, day = content
        super().__init__(parent, self.mealplan._days[day])

    def deep_data(self, row: int, col: int, is_display: bool) -> Optional[str]:
        ing, amount = self.content[row]
        if col == 0:
            if is_display:
                return ing.name
            else:
                return ing._id
        elif col == 1:
            if is_display:
                return f"{amount} {ing.unit}"
            else:
                return str(amount)
        return None
   
    def set_data(self, row: int, col: int, value: Any) -> bool:
        comp, _ = self.content[row]
        if col == 0:
            self.mealplan._change_component(self.content, row, value)
        elif col == 1:
            self.mealplan._change_amount(self.content, row, value) 
        else:
            return False

        self.refresh.emit()
        return True

    def new_entry(self) -> None:
        new_id, ok = QInputDialog.getText(cast(Optional[QWidget], self.parent()), "New meal",
            "Please specify the name of an ingredient or recipe:")
        self.mealplan._new_component(self.content, new_id)

    def delete_entry(self, row: int) -> None:
        self.mealplan._remove_component(self.content, row)

class MealplanDayTable(FixTable):
    model: MealplanDayModel
    ModelClass = MealplanDayModel
    item_name = "meal"
    default_widths = [(1,100),]
    fixed_widths = [1]
    stretch_widths = [0]

    def __init__(self, mealplan: Mealplan, day: int) -> None:
        super().__init__((mealplan, day))


class ShoppingListModel(CoreTableModel):
    content: list[list[str]]
    header_names = ["Ingredient", "Amount"]
    align = ["right", ""]
    not_editable = [0, 1]
    
    def get_data(self, row: int, col: int) -> Optional[str]:
        return self.content[row][col]

class ShoppingListTable(CoreTable):
    model: ShoppingListModel
    ModelClass = ShoppingListModel
    item_name = None
    default_widths = [(1,100),]
    fixed_widths = [1]
    stretch_widths = [0]
