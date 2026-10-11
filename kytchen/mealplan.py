from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, cast

if TYPE_CHECKING:
    from .cookbook import Cookbook
    from .ingredient import Ingredient

from decimal import Decimal

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QStackedWidget,
)
from .views import (
    DashboardTable,
    DashboardTableModel,
    CoreTableModel,
    EntriesTable,
    DetailView,
    CoreTable,
    num_string,
    amount_string,
    metric_strings,
    symbol_button,
    Subtitle,
    Heading,
    no_margin,
)


DAY_LIST_STYLE = """
QListWidget {
    background: transparent;
    border: none;
    outline: 0;
}
QListWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QListWidget::item:hover:!selected {
    background: rgba(128, 128, 128, 30);
}
QListWidget::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}
"""


class Mealplan:
    def __init__(self, cookbook: Cookbook, name: str = "") -> None:
        self.name = name
        self.cookbook = cookbook
        self._days: list[list[list[Any]]] = []
        self.window: Optional[MealplanView] = None

    def export(self) -> dict[str, Any]:
        data: dict[str, Any] = {"name": self.name}
        days = []
        for day in self._days:
            days.append([[e[0]._id, str(e[1])] for e in day])
        data["days"] = days
        return data

    @classmethod
    def load(cls, data: dict[str, Any], cookbook: Cookbook) -> Mealplan:
        self = cls(cookbook, data["name"])
        for day in data["days"]:
            new_day: list[list[Any]] = []
            for entry in day:
                cookbook.add_entry(self, new_day, entry[0], entry[1], strict=True)
            self._days.append(new_day)
        return self

    def new_day(self) -> None:
        self._days.append([])

    def display_name(self) -> str:
        return self.name if self.name else "Untitled meal plan"

    def get_ingredients(self) -> dict[Ingredient, Decimal]:
        total: dict[Ingredient, Decimal] = {}
        for day in self._days:
            for component, amount in day:
                for ingredient, value in component.get_ingredients(amount).items():
                    total[ingredient] = total.get(ingredient, Decimal(0)) + value
        return {ingredient: value for ingredient, value in total.items() if value != 0}

    def remove_day(self, day: int) -> None:
        for component, _ in self._days.pop(day):
            self.cookbook.unlink_component(self, component)

    def move_day(self, day: int, offset: int) -> bool:
        target = day + offset
        if not (0 <= day < len(self._days) and 0 <= target < len(self._days)):
            return False
        self._days[day], self._days[target] = self._days[target], self._days[day]
        return True

    def get_shopping_list(self) -> list[list[str]]:
        ls = []
        for component, amount in self.get_ingredients().items():
            ls.append(
                [
                    component.display_name(),
                    amount_string(num_string(amount), component.unit),
                ]
            )
        ls.sort(key=lambda entry: entry[0].lower())
        return ls

    def get_metric(
        self, metric: str, ingredients: Optional[dict[Ingredient, Decimal]] = None
    ) -> Decimal:
        if len(self._days) == 0:
            return Decimal(0)
        if ingredients is None:
            ingredients = self.get_ingredients()
        total = sum(
            (
                element.get_metric(metric) * amount
                for element, amount in ingredients.items()
            ),
            Decimal(0),
        )
        return total / len(self._days)

    def get_metrics(self) -> dict[str, Decimal]:
        ingredients = self.get_ingredients()
        return {
            metric: self.get_metric(metric, ingredients)
            for metric in self.cookbook.metrics
        }

    def get_day_metrics(self, day: int) -> dict[str, Decimal]:
        return {
            metric: sum(
                (
                    component.get_metric(metric) * amount
                    for component, amount in self._days[day]
                ),
                Decimal(0),
            )
            for metric in self.cookbook.metrics
        }

    def __str__(self) -> str:
        string = self.display_name()
        string += "\n\n"
        for i, day in enumerate(self._days):
            string += f"DAY {i + 1}"
            for item, amount in day:
                string += f"\n- {item.display_name()} ({amount_string(str(amount), item.unit)})"
        string += f"\nDaily average: {', '.join(metric_strings(self.get_metrics()))}\n"
        return string

    def __repr__(self) -> str:
        return self.name

    def get_window(self) -> None:
        if self.window is None:
            self.window = MealplanView(self, self.cookbook.window)
        self.window.open()

    def _clear(self) -> None:
        if self.window != None:
            self.window.deleteLater()
            self.window = None
        for i in range(len(self._days)):
            self.remove_day(0)

    def _col(self, col: int, metrics: list[str]) -> Optional[str]:
        if col == 0:
            return self.name
        elif col <= len(metrics):
            return num_string(self.get_metric(metrics[col - 1]))
        else:
            return None


class MealplanDashModel(DashboardTableModel):
    content: list[Mealplan]
    placeholders = {0: "Untitled meal plan"}

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        self.header_names = (
            ["Meal plan name"] + [f"{metric}/day" for metric in cookbook.metrics] + [""]
        )
        self.align = ["left"] + ["right"] * len(cookbook.metrics)
        self.not_editable = list(range(1, len(self.header_names)))
        super().__init__(parent, cookbook.mealplans)

    def get_data(self, row: int, col: int) -> Optional[str]:
        mealplan = self.content[row]
        return mealplan._col(col, self.cookbook.metrics)

    def set_data(self, row: int, col: int, value: Any) -> bool:
        mealplan = self.content[row]
        if col == 0:
            mealplan.name = value
            if mealplan.window != None:
                mealplan.window.refresh_name()
        return True

    def new_entry(self) -> None:
        mealplan = Mealplan(self.cookbook)
        mealplan.new_day()
        self.cookbook.register_mealplan(mealplan)

    def delete_entry(self, row: int) -> None:
        self.cookbook.delete_mealplan(row, cast(Optional[QWidget], self.parent()))


class MealplanDashTable(DashboardTable):
    ModelClass = MealplanDashModel
    item_name = "meal plan"
    stretch_widths = [0]

    def __init__(self, cookbook: Cookbook) -> None:
        super().__init__(cookbook)
        self.resize_columns([], [], [], list(range(1, self.model.ncols - 1)))


class MealplanView(DetailView):
    metric_suffix = "/day"

    def __init__(self, mealplan: Mealplan, parent: Optional[QWidget]) -> None:
        super().__init__(mealplan, parent, 600, 700)
        self.mealplan = mealplan

        self.shopping_view = ShoppingListTable(self.mealplan.get_shopping_list())
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(10)
        self.body.addLayout(self.main_layout)
        self.sidebar_container = QVBoxLayout()
        self.sidebar_container.setSpacing(10)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(140)
        self.sidebar.setStyleSheet(DAY_LIST_STYLE)
        self.sidebar_container.addWidget(self.sidebar)
        self.sidebar.currentRowChanged.connect(self.menu_action)
        self.sidebar_buttons_widget = QWidget()
        self.sidebar_buttons = QHBoxLayout(self.sidebar_buttons_widget)
        no_margin(self.sidebar_buttons)
        self.sidebar_container.addWidget(self.sidebar_buttons_widget)
        self.button_add = symbol_button("+", "New day")
        self.button_remove = symbol_button("−", "Remove the selected day")
        self.button_up = symbol_button("↑", "Move the selected day up")
        self.button_down = symbol_button("↓", "Move the selected day down")
        self.button_add.clicked.connect(self.new_day)
        self.button_remove.clicked.connect(self.remove_day)
        self.button_up.clicked.connect(lambda: self.move_day(-1))
        self.button_down.clicked.connect(lambda: self.move_day(1))
        self.sidebar_buttons.setSpacing(4)
        self.sidebar_buttons_widget.setFixedWidth(self.sidebar.width())
        self.sidebar_buttons.addWidget(self.button_add)
        self.sidebar_buttons.addWidget(self.button_remove)
        self.sidebar_buttons.addStretch()
        self.sidebar_buttons.addWidget(self.button_up)
        self.sidebar_buttons.addWidget(self.button_down)

        self.stack = QStackedWidget()
        self.page_title = Heading("")
        self.page_details = Subtitle("")
        page_heading = QHBoxLayout()
        page_heading.setSpacing(10)
        page_heading.addWidget(
            self.page_title, alignment=Qt.AlignmentFlag.AlignBaseline
        )
        page_heading.addWidget(
            self.page_details, alignment=Qt.AlignmentFlag.AlignBaseline
        )
        page_heading.addStretch()
        content = QVBoxLayout()
        content.setSpacing(10)
        content.addLayout(page_heading)
        content.addWidget(self.stack)
        self.main_layout.addLayout(self.sidebar_container)
        self.main_layout.addLayout(content, 1)

        self.sidebar.addItems(["Shopping list"])
        self.stack.addWidget(self.shopping_view)
        self.views: list[MealplanDayTable] = []
        for day in self.mealplan._days:
            self.add_day_view(day)
        self.sidebar.setCurrentRow(0)

        self.set_editing(False)
        self.refresh()

    def menu_action(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.refresh_page()

    def add_day_view(self, day: list[list[Any]]) -> None:
        view = MealplanDayTable(self.mealplan, day)
        view.set_editable(self.editing)
        view.model.refresh.connect(self.refresh)
        view.model.modelReset.connect(self.refresh)
        self.views.append(view)
        self.stack.addWidget(view)
        self.sidebar.addItem(f"Day {len(self.views)}")

    def new_day(self) -> None:
        self.mealplan.new_day()
        self.add_day_view(self.mealplan._days[-1])
        self.refresh()

    def selected_day(self) -> Optional[int]:
        row = self.sidebar.currentRow()
        return row - 1 if row >= 1 else None

    def reload_days(self) -> None:
        for view, day in zip(self.views, self.mealplan._days):
            view.model.beginResetModel()
            view.model.content = day
            view.model.endResetModel()

    def remove_day(self) -> None:
        day = self.selected_day()
        if day is None:
            return
        self.mealplan.remove_day(day)
        self.sidebar.takeItem(self.sidebar.count() - 1)
        view = self.views.pop()
        self.stack.removeWidget(view)
        view.deleteLater()
        self.reload_days()
        self.sidebar.setCurrentRow(min(day + 1, len(self.views)))
        self.refresh()

    def move_day(self, offset: int) -> None:
        day = self.selected_day()
        if day is None or not self.mealplan.move_day(day, offset):
            return
        self.reload_days()
        self.sidebar.setCurrentRow(day + offset + 1)
        self.refresh()

    def update_day_buttons(self) -> None:
        day = self.selected_day()
        self.button_remove.setEnabled(day is not None)
        self.button_up.setEnabled(day is not None and day > 0)
        self.button_down.setEnabled(
            day is not None and day < len(self.mealplan._days) - 1
        )

    def set_editing(self, edit: bool) -> None:
        super().set_editing(edit)
        for view in self.views:
            view.set_editable(edit)
        self.sidebar_buttons_widget.setVisible(edit)

    def refresh(self) -> None:
        super().refresh()
        self.shopping_view.model.beginResetModel()
        self.shopping_view.model.content = self.mealplan.get_shopping_list()
        self.shopping_view.model.endResetModel()
        self.refresh_page()

    def refresh_page(self) -> None:
        self.update_day_buttons()
        index = self.stack.currentIndex()
        if index <= 0:
            count = len(self.shopping_view.model.content)
            self.page_title.setText("Shopping list")
            self.page_details.setText(
                f"{count} ingredient{'' if count == 1 else 's'}" if count else ""
            )
        else:
            self.page_title.setText(f"Day {index}")
            self.page_details.setText(
                " · ".join(metric_strings(self.mealplan.get_day_metrics(index - 1)))
            )


class MealplanDayTable(EntriesTable):
    item_name = "meal"
    empty_message = "No meals planned for this day yet."


class ShoppingListModel(CoreTableModel):
    content: list[list[str]]
    header_names = ["Ingredient", "Amount"]
    align = ["left", "right"]
    not_editable = [0, 1]

    def get_data(self, row: int, col: int) -> Optional[str]:
        return self.content[row][col]


class ShoppingListTable(CoreTable):
    model: ShoppingListModel
    ModelClass = ShoppingListModel
    item_name = None
    empty_message = "Nothing to buy yet. Add some meals to your days."
    default_widths = [(1, 130)]
    fixed_widths = [1]
    stretch_widths = [0]
