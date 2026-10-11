from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Union, cast
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .cookbook import Cookbook
    from .mealplan import Mealplan
    from .recipe import Recipe

import uuid
from decimal import Decimal
from .views import SortTableModel, SortTable, ask_name, num, Numeric


class Ingredient:
    def __init__(
        self,
        name: str = "",
        metrics: Optional[dict[str, Numeric]] = None,
        unit: str = "",
        id_name: Optional[str] = None,
    ) -> None:
        self.name = name
        if metrics is None:
            metrics = {}
        self.metrics = {metric: num(value) for metric, value in metrics.items()}
        self.unit = unit
        self._used: dict[Union[Recipe, Mealplan], int] = {}
        self._id = id_name if id_name is not None else str(uuid.uuid4())

    def export(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["name"] = self.name
        data["metrics"] = {metric: str(value) for metric, value in self.metrics.items()}
        data["unit"] = self.unit
        data["id"] = self._id
        return data

    @classmethod
    def load(cls, data: dict[str, Any]) -> Ingredient:
        return cls(data["name"], data["metrics"], data["unit"], data["id"])

    def get_metric(self, metric: str) -> Decimal:
        return self.metrics.get(metric, Decimal(0))

    def display_name(self) -> str:
        return self.name if self.name else "Unnamed ingredient"

    def choice_label(self) -> str:
        if self.unit:
            return f"{self.display_name()} ({self.unit})"
        return self.display_name()

    def __str__(self) -> str:
        if not self.metrics:
            return self.name
        metrics = ", ".join(
            f"{value} {metric}/{self.unit}" for metric, value in self.metrics.items()
        )
        return f"{self.name} ({metrics})"

    def __repr__(self) -> str:
        return self.__str__()

    def _col(self, col: int, metrics: list[str]) -> Optional[str]:
        if col == 0:
            return self.name
        elif col < 1 + len(metrics):
            return str(self.get_metric(metrics[col - 1]))
        elif col == 1 + len(metrics):
            return self.unit
        return None

    def get_ingredients(self, amount: Decimal) -> dict[Ingredient, Decimal]:
        return {self: amount}


class IngredientModel(SortTableModel):
    content: list[Ingredient]
    placeholders = {0: "Unnamed ingredient"}

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        self.header_names = (
            ["Ingredient"]
            + [f"{metric}/unit" for metric in cookbook.metrics]
            + ["Unit"]
        )
        self.align = ["left"] + ["right"] * len(cookbook.metrics) + ["left"]
        super().__init__(parent, cookbook.ingredients)

    def get_data(self, row: int, col: int) -> Optional[str]:
        ing = self.content[row]
        return ing._col(col, self.cookbook.metrics)

    def set_data(self, row: int, col: int, value: Any) -> bool:
        ing = self.content[row]
        metrics = self.cookbook.metrics
        if col == 0:
            ing.name = value
        elif col < 1 + len(metrics):
            try:
                value = num(value)
            except:
                return False
            ing.metrics[metrics[col - 1]] = value
        elif col == 1 + len(metrics):
            ing.unit = value

        return True

    def new_entry(self) -> None:
        name = ask_name(cast(Optional[QWidget], self.parent()), "ingredient")
        if name is not None:
            self.cookbook.register_ingredient(Ingredient(name))

    def delete_entry(self, row: int) -> None:
        self.cookbook.delete_ingredient(row, cast(Optional[QWidget], self.parent()))


class IngredientTable(SortTable):
    ModelClass = IngredientModel
    item_name = "ingredient"
    stretch_widths = [0]

    def __init__(self, cookbook: Cookbook) -> None:
        super().__init__(cookbook)
        self.resize_columns(
            [(self.model.ncols - 1, 100)], [], [], list(range(1, self.model.ncols - 1))
        )
