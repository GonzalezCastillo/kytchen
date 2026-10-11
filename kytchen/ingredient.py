from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Union, cast
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .cookbook import Cookbook
    from .mealplan import Mealplan
    from .recipe import Recipe

from decimal import Decimal
from .views import SortTableModel, SortTable, create_new, num, Numeric

class Ingredient():
    def __init__(self, id_name: str, name: str = "", metrics: Optional[dict[str, Numeric]] = None, unit: str = "") -> None:
        self.name = name
        if metrics is None:
            metrics = {}
        self.metrics = {metric: num(value) for metric, value in metrics.items()}
        self.unit = unit
        self._used: dict[Union[Recipe, Mealplan], int] = {}
        self._id = id_name
    
    def export(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        data["name"] = self.name
        data["metrics"] = {metric: str(value) for metric, value in self.metrics.items()}
        data["unit"] = self.unit
        data["id"] = self._id
        return data

    @classmethod
    def load(cls, data: dict[str, Any]) -> Ingredient:
        if "metrics" in data:
            metrics = data["metrics"]
        else:
            metrics = {"kcal": data["calories"]}
        return cls(data["id"], data["name"], metrics, data["unit"])

    def get_metric(self, metric: str) -> Decimal:
        return self.metrics.get(metric, Decimal(0))

    def __str__(self) -> str:
        if not self.metrics:
            return self.name
        metrics = ", ".join(f"{value} {metric}/{self.unit}" for metric, value in self.metrics.items())
        return f"{self.name} ({metrics})"
    
    def __repr__(self) -> str:
        return self.__str__()

    def _col(self, col: int, metrics: list[str], string: bool = True) -> Union[str, Decimal, None]:
        if col == 0:
            return self._id
        elif col == 1:
            return self.name
        elif col < 2 + len(metrics):
            value = self.get_metric(metrics[col - 2])
            if string:
                return str(value)
            else:
                return value
        elif col == 2 + len(metrics):
            return self.unit
        return None

    def get_ingredients(self, amount: Decimal) -> dict[Ingredient, Decimal]:
        return {self: amount}



class IngredientModel(SortTableModel):
    content: list[Ingredient]
    align = ["", "left"]

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        self.header_names = (["ID", "Ingredient"]
            + [f"{metric}/unit" for metric in cookbook.metrics] + ["Unit"])
        super().__init__(parent, cookbook.ingredients)

    def get_data(self, row: int, col: int) -> Union[str, Decimal, None]:
        ing = self.content[row]
        return ing._col(col, self.cookbook.metrics)


    def set_data(self, row: int, col: int, value: Any) -> bool:
        ing = self.content[row]
        metrics = self.cookbook.metrics
        if col == 0:
            self.cookbook.update_component_id(ing, value) 
        elif col == 1:
            ing.name = value
        elif col < 2 + len(metrics):
            try:
                value = num(value)
            except:
                return False
            ing.metrics[metrics[col - 2]] = value
        elif col == 2 + len(metrics):
            ing.unit = value
        
        return True        

    def new_entry(self) -> None:
        def create_function(new_id: str) -> bool:
            ing = Ingredient(new_id)
            return self.cookbook.register_ingredient(ing)
        create_new(cast(Optional[QWidget], self.parent()), "ingredient", create_function)
    
    def delete_entry(self, row: int) -> None:
        self.cookbook.delete_ingredient(row, cast(Optional[QWidget], self.parent()))

 
class IngredientTable(SortTable):
    ModelClass = IngredientModel
    item_name = "ingredient"
    default_widths = [(0, 150)]
    stretch_widths = [1]

    def __init__(self, cookbook: Cookbook) -> None:
        super().__init__(cookbook)
        columns = list(range(2, self.model.ncols))
        self.resize_columns([(col, 100) for col in columns], columns, [])

