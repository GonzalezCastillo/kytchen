from typing import TYPE_CHECKING, Any, Optional, Union, cast
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .cookbook import Cookbook
    from .mealplan import Mealplan
    from .recipe import Recipe

from decimal import Decimal
from .views import SortTableModel, SortTable, create_new, num, Numeric

class Ingredient():
    def __init__(self, id_name: str, name: str = "", calories: Numeric = Decimal(0), unit: str = "") -> None:
        self.name = name
        self.calories = num(calories)
        self.unit = unit
        self._used: dict[Union[Recipe, Mealplan], int] = {}
        self._id = id_name
    
    def export(self) -> dict[str, Any]:
        data = {}
        data["name"] = self.name
        data["calories"] = str(self.calories)
        data["unit"] = self.unit
        data["id"] = self._id
        return data

    @classmethod
    def load(cls, data: dict[str, Any]) -> Ingredient:
        return cls(data["id"], data["name"], Decimal(data["calories"]), data["unit"])

    def get_calories(self) -> Decimal:
        return self.calories

    def __str__(self) -> str:
        return f"{self.name} ({self.calories} kcal/{self.unit})"
    
    def __repr__(self) -> str:
        return self.__str__()

    def _col(self, col: int, string: bool = True) -> Union[str, Decimal, None]:
        if col == 0:
            return self._id
        elif col == 1:
            return self.name
        elif col == 2:
            if string:
                return str(self.calories)
            else:
                return self.calories
        elif col == 3:
            return self.unit
        return None

    def get_ingredients(self, amount: Decimal) -> dict[Ingredient, Decimal]:
        return {self: amount}



class IngredientModel(SortTableModel):
    content: list[Ingredient]
    header_names = ["ID", "Ingredient", "kcal/unit", "Unit"]
    align = ["", "left", "", ""]

    def __init__(self, parent: Optional[QWidget], cookbook: Cookbook) -> None:
        self.cookbook = cookbook
        super().__init__(parent, cookbook.ingredients)

    def get_data(self, row: int, col: int) -> Union[str, Decimal, None]:
        ing = self.content[row]
        return ing._col(col)


    def set_data(self, row: int, col: int, value: Any) -> bool:
        ing = self.content[row]
        if col == 0:
            self.cookbook.update_component_id(ing, value) 
        elif col == 1:
            ing.name = value
        elif col == 2:
            try:
                value = num(value)
            except:
                return False
            ing.calories = value
        elif col == 3:
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
    default_widths = [(0, 150), (2, 100), (3, 100)]
    fixed_widths = [2, 3]
    stretch_widths = [1]

