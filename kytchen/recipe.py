from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Union, cast

if TYPE_CHECKING:
    from .cookbook import Cookbook
    from .ingredient import Ingredient
    from .mealplan import Mealplan

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QHeaderView,
    QFileDialog,
)
import uuid
from decimal import Decimal

from .numeric import num_string, exact_string, json_number, metric_strings, Numeric
from .widgets import DetailView, ServingsBox, ask_name, show_error, no_margin
from .delegates import TextDelegate
from .tables import (
    DashboardTable,
    DashboardTableModel,
    CoreTableModel,
    FixTable,
    EntriesTable,
)


class Recipe:
    unit = "serv"

    def __init__(
        self,
        cookbook: Cookbook,
        name: str = "",
        category: str = "",
        steps: Optional[list[str]] = None,
        id_name: Optional[str] = None,
    ) -> None:
        self.name = name
        if steps == None:
            steps = []
        self.steps = steps
        self.category = category

        self.cookbook = cookbook
        self.amounts: list[list[Any]] = []
        self._id = id_name if id_name is not None else str(uuid.uuid4())
        self._used: dict[Union[Recipe, Mealplan], int] = {}
        self.window: Optional[RecipeView] = None

    def export(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "category": self.category,
            "id": self._id,
        }
        amounts = []
        for component, amount in self.amounts:
            amounts.append([component._id, str(amount)])

        data["steps"] = list(self.steps)
        data["amounts"] = amounts

        return data

    @classmethod
    def load_steps(cls, data: dict[str, Any], cookbook: Cookbook) -> Recipe:
        id_name = data["id"]
        name = data["name"]
        category = data["category"]
        steps = data["steps"]
        if not all(isinstance(step, str) for step in steps):
            raise ValueError("invalid step")
        return cls(cookbook, name, category, list(steps), id_name)

    def load_amounts(self, data: dict[str, Any]) -> None:
        for entry in data["amounts"]:
            self.new_component(entry[0], entry[1], True)

    def change_amounts(
        self,
        index: int,
        component: Optional[str] = None,
        amount: Optional[Numeric] = None,
        strict: bool = False,
    ) -> bool:
        return self.cookbook.change_entry(
            self, self.amounts, index, component, amount, strict
        )

    def new_component(
        self, id_name: str, amount: Numeric = Decimal(0), strict: bool = False
    ) -> bool:
        return self.cookbook.add_entry(self, self.amounts, id_name, amount, strict)

    def get_amounts(
        self, servings: Union[Decimal, int] = 1
    ) -> list[tuple[Union[Ingredient, Recipe], Decimal]]:
        amounts = []
        for component, amount in self.amounts:
            amounts.append((component, amount * servings))
        return amounts

    def get_metric(self, metric: str, servings: Union[Decimal, int] = 1) -> Decimal:
        total = Decimal(0)
        amounts = self.get_amounts(servings)
        for component, amount in amounts:
            total += amount * component.get_metric(metric)
        return total

    def get_metrics(self, servings: Union[Decimal, int] = 1) -> dict[str, Decimal]:
        return {
            metric: self.get_metric(metric, servings)
            for metric in self.cookbook.metrics
        }

    def display_name(self) -> str:
        return self.name if self.name else "Untitled recipe"

    def choice_label(self) -> str:
        return f"{self.display_name()} (recipe)"

    def card(self, servings: Union[Decimal, int] = 1) -> dict[str, Any]:
        ingredients = []
        for component, amount in self.get_amounts(servings):
            entry: dict[str, Any] = {
                "name": component.display_name(),
                "amount": json_number(amount),
                "unit": component.unit,
            }
            if isinstance(component, Recipe):
                entry["recipe"] = component.card(amount)
            ingredients.append(entry)
        return {
            "name": self.display_name(),
            "category": self.category,
            "servings": json_number(Decimal(servings)),
            "metrics": {
                metric: json_number(value)
                for metric, value in self.get_metrics(servings).items()
            },
            "metrics_per_serving": {
                metric: json_number(value)
                for metric, value in self.get_metrics().items()
            },
            "ingredients": ingredients,
            "steps": list(self.steps),
        }

    def __repr__(self) -> str:
        metrics = metric_strings(self.get_metrics(), "/serv")
        if not metrics:
            return self.name
        return f"{self.name} ({', '.join(metrics)})"

    def _col(self, col: int, metrics: list[str]) -> Optional[str]:
        if col == 0:
            return self.name
        elif col == 1:
            return self.category
        elif col < 2 + len(metrics):
            return num_string(self.get_metric(metrics[col - 2]))
        else:
            return None

    def get_ingredients(
        self, servings: Union[Decimal, int]
    ) -> dict[Ingredient, Decimal]:
        total: dict[Ingredient, Decimal] = {}
        for component, amount in self.amounts:
            add = component.get_ingredients(amount * servings)
            for c, a in add.items():
                if c in total:
                    total[c] += a
                else:
                    total[c] = a
        return total

    def get_window(self) -> None:
        if self.window is None:
            self.window = RecipeView(self, self.cookbook.window)
        self.window.open()


class RecipeDashModel(DashboardTableModel):
    content: list[Recipe]
    placeholders = {0: "Untitled recipe"}

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        self.header_names = (
            ["Recipe name", "Category"]
            + [f"{metric}/serv" for metric in cookbook.metrics]
            + [""]
        )
        self.align = ["left", "left"] + ["right"] * len(cookbook.metrics)
        self.not_editable = list(range(2, len(self.header_names)))
        super().__init__(parent, cookbook.recipes)

    def get_data(self, row: int, col: int) -> Optional[str]:
        recipe = self.content[row]
        return recipe._col(col, self.cookbook.metrics)

    def set_data(self, row: int, col: int, value: Any) -> bool:
        recipe = self.content[row]
        if col == 0:
            recipe.name = value
            if recipe.window != None:
                recipe.window.refresh_name()
        elif col == 1:
            recipe.category = value

        return True

    def new_entry(self) -> None:
        name = ask_name(cast(Optional[QWidget], self.parent()), "recipe")
        if name is not None:
            self.cookbook.register_recipe(Recipe(self.cookbook, name))

    def delete_entry(self, row: int) -> None:
        self.cookbook.delete_recipe(row, cast(Optional[QWidget], self.parent()))


class RecipeDashTable(DashboardTable):
    ModelClass = RecipeDashModel
    item_name = "recipe"
    default_widths = [(1, 120)]
    stretch_widths = [0]

    def __init__(self, cookbook: Cookbook) -> None:
        super().__init__(cookbook)
        self.resize_columns([], [], [], list(range(2, self.model.ncols - 1)))


class RecipeView(DetailView):
    metric_suffix = "/serv"

    def __init__(self, recipe: Recipe, parent: Optional[QWidget]) -> None:
        super().__init__(recipe, parent, 600, 760)
        self.recipe = recipe

        self.servings_box = ServingsBox()
        self.servings_box.valueChanged.connect(lambda: self.update_servings())
        self.servings_row = QWidget()
        servings_layout = QHBoxLayout(self.servings_row)
        no_margin(servings_layout)
        servings_layout.addWidget(QLabel("Servings"))
        servings_layout.addWidget(self.servings_box)
        servings_layout.addStretch()
        self.body.addWidget(self.servings_row)

        self.amounts_table = AmountsTable(recipe, recipe.amounts)
        self.amounts_table.model.refresh.connect(self.refresh)
        self.amounts_table.model.modelReset.connect(self.refresh)
        self.body.addWidget(self.amounts_table)

        self.steps_table = StepsTable(recipe.steps)
        self.body.addWidget(self.steps_table)

        self.save_button = QPushButton("Save…")
        self.save_button.clicked.connect(self.save_card)
        self.controls.insertWidget(1, self.save_button)

        self.set_editing(False)
        self.refresh()

    def set_editing(self, edit: bool) -> None:
        super().set_editing(edit)
        self.steps_table.set_editable(edit)
        self.amounts_table.set_editable(edit)
        self.servings_row.setVisible(not edit)
        self.save_button.setVisible(not edit)
        self.update_servings()

    def update_servings(self) -> None:
        self.amounts_table.model.set_servings(
            Decimal(1) if self.editing else self.servings_box.servings()
        )

    def save_card(self) -> None:
        servings = self.servings_box.servings()
        plural = "serving" if servings == 1 else "servings"
        name = f"{self.recipe.display_name()} ({exact_string(servings)} {plural}).json"
        name = name.replace("/", "-")
        folder = (
            Path(self.recipe.cookbook.path).parent
            if self.recipe.cookbook.path
            else Path.home()
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Save recipe", str(folder / name), "JSON (*.json)"
        )
        if not path:
            return
        if not path.endswith(".json"):
            path += ".json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.recipe.card(servings), f, indent=2, ensure_ascii=False)
        except OSError as error:
            show_error(self, f"Could not save {path}: {error}")


class StepsTableModel(CoreTableModel):
    content: list[str]
    header_names = ["Step"]
    align = ["left"]
    placeholders = {0: "Insert a step…"}

    def get_data(self, row: int, col: int) -> Optional[str]:
        return self.content[row] if col == 0 else None

    def set_data(self, row: int, col: int, value: Any) -> bool:
        if col != 0:
            return False
        self.content[row] = value
        return True

    def new_entry(self) -> None:
        self.content.append("")

    def delete_entry(self, row: int) -> None:
        del self.content[row]


class StepsTable(FixTable):
    model: StepsTableModel
    ModelClass = StepsTableModel
    item_name = "step"
    stretch_widths = [0]

    def __init__(self, steps: list[str]) -> None:
        super().__init__(steps)
        self.table.setWordWrap(True)
        self.table.setItemDelegateForColumn(0, TextDelegate(self.table))
        rows = cast(QHeaderView, self.table.verticalHeader())
        rows.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)


class AmountsTable(EntriesTable):
    item_name = "ingredient"
