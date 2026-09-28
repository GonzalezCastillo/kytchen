from typing import TYPE_CHECKING, Any, Optional, Union
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .app import MainWindow

import json
from decimal import Decimal

from .ingredient import Ingredient
from .recipe import Recipe
from .mealplan import Mealplan
from .views import show_error

def can_delete_component(component: Union[Ingredient, Recipe], view: Optional[QWidget] = None) -> bool:
    if component._used:
        if view:
            used_name = list(component._used.keys())[0].name
            show_error(view,
                f"Cannot delete {component.name}. It is used in {used_name}.")
        return False
    else:
        return True

class Cookbook():
    def __init__(self) -> None:
        self._components: dict[str, Union[Ingredient, Recipe]] = {}
        self.ingredients: list[Ingredient] = []
        self.recipes: list[Recipe] = []
        self.mealplans: list[Mealplan] = []
        self.path: Optional[str] = None
        self.window: Optional[MainWindow] = None

    @classmethod
    def load(cls, path: str) -> Cookbook:
        with open(path, "r") as f:
            data = json.load(f)
        self = cls()
        for ing in data["ingredients"]:
            ing = Ingredient.load(ing)
            if not self.register_ingredient(ing):
                raise ValueError("duplicate component ID")
        for rec in data["recipes"]:
            rec = Recipe.load_steps(rec, self)
            if not self.register_recipe(rec):
                raise ValueError("duplicate component ID")
        for recipe, rec in zip(self.recipes, data["recipes"]):
            recipe.load_amounts(rec)
        for plan in data["mealplans"]:
            plan = Mealplan.load(plan, self)
            self.register_mealplan(plan)
        self.path = path
        return self

    def save(self, path: Optional[str] = None) -> None:
        data: dict[str, list[dict[str, Any]]] = {"ingredients": [], "recipes": [], "mealplans": []}
        for ing in self.ingredients:
            data["ingredients"].append(ing.export())
        for rec in self.recipes:
            data["recipes"].append(rec.export())
        for plan in self.mealplans:
            data["mealplans"].append(plan.export())
        if path == None:
            path = self.path
        if path is None:
            raise ValueError("no cookbook path specified")
        with open(path, "w") as f:
            json.dump(data, f)

    def set_path(self, path: Optional[str]) -> None:
        self.path = path

    def get_name(self) -> str:
        if self.path != None:
            return self.path.split("/")[-1].split("\\")[-1].strip(".js")
        else:
            return "New cookbook"

    def register_component(self, component: Union[Ingredient, Recipe]) -> bool:
        if component._id in self._components:
            return False
        self._components[component._id] = component
        return True

    def register_ingredient(self, ingredient: Ingredient) -> bool:
        if self.register_component(ingredient):
            self.ingredients.append(ingredient)
            return True
        else:
            return False

    def register_recipe(self, recipe: Recipe) -> bool:
        if self.register_component(recipe):
            self.recipes.append(recipe)
            return True
        else:
            return False

    def register_mealplan(self, mealplan: Mealplan) -> None:
        self.mealplans.append(mealplan)

    def update_component_id(self, component: Union[Ingredient, Recipe], new: str) -> bool:
        if new in self._components:
            return False
        self._components[new] = self._components.pop(component._id)
        component._id = new
        return True

    def delete_ingredient(self, index: int, view: Optional[QWidget] = None) -> None:
        ing = self.ingredients[index]
        if can_delete_component(ing, view):
            del self.ingredients[index]
            del self._components[ing._id]

    def delete_recipe(self, index: int, view: Optional[QWidget] = None) -> None:
        recipe = self.recipes[index]
        if not can_delete_component(recipe, view):
            return
        if recipe.window != None:
            recipe.window.deleteLater()
            recipe.window = None
        for component, _ in recipe.amounts:
            self.unlink_component(recipe, component)
        del self.recipes[index]
        del self._components[recipe._id]

    def delete_mealplan(self, index: int) -> None:
        mealplan = self.mealplans[index]
        mealplan._clear()
        del self.mealplans[index]

    def link_component(self, origin: Union[Recipe, Mealplan], name_id: str) -> Optional[Union[Ingredient, Recipe]]:
        if name_id in self._components:
            obj = self._components[name_id]
            pending = [obj]
            visited = set()
            while pending:
                component = pending.pop()
                if component is origin:
                    return None
                if component in visited:
                    continue
                visited.add(component)
                if isinstance(component, Recipe):
                    pending.extend(entry[0] for entry in component.amounts)
            obj._used.setdefault(origin, 0)
            obj._used[origin] += 1
            return obj
        else:
            return None

    def unlink_component(self, origin: Union[Recipe, Mealplan], old: Union[Ingredient, Recipe]) -> None:
        old._used[origin] -= 1
        if old._used[origin] == 0:
            del old._used[origin]

    def change_link(self, origin: Union[Recipe, Mealplan], old: Union[Ingredient, Recipe], new_id: str) -> Optional[Union[Ingredient, Recipe]]:
        new = self.link_component(origin, new_id)
        if new:
            self.unlink_component(origin, old)
            return new
        return None

    def is_empty(self) -> bool:
        return len(self._components) == 0
