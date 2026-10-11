from __future__ import annotations
from typing import TYPE_CHECKING, Any, Optional, Union
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from .app import MainWindow

import json
from decimal import Decimal
from pathlib import Path

from .ingredient import Ingredient
from .recipe import Recipe
from .mealplan import Mealplan
from .views import show_error, ask_confirmation, num, Numeric

DEFAULT_METRICS = ["kcal"]


def parse_amount(amount: Numeric, strict: bool) -> Optional[Decimal]:
    try:
        return num(amount)
    except (ValueError, TypeError, ArithmeticError):
        if strict:
            raise ValueError("invalid amount")
        return None


def can_delete_component(
    component: Union[Ingredient, Recipe], view: Optional[QWidget] = None
) -> bool:
    if component._used:
        if view:
            used_name = list(component._used.keys())[0].display_name()
            show_error(
                view,
                f"Cannot delete {component.display_name()}. It is used in {used_name}.",
            )
        return False
    else:
        return True


def confirm_delete(kind: str, name: str, view: Optional[QWidget]) -> bool:
    return view is None or ask_confirmation(
        view, f"Delete the {kind} '{name}'? This cannot be undone."
    )


class Cookbook:
    def __init__(self) -> None:
        self._components: dict[str, Union[Ingredient, Recipe]] = {}
        self.metrics: list[str] = list(DEFAULT_METRICS)
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
        self.metrics.clear()
        for metric in data["metrics"]:
            if not self.add_metric(metric):
                raise ValueError("invalid or duplicate metric")
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
        data: dict[str, list[Any]] = {
            "metrics": list(self.metrics),
            "ingredients": [],
            "recipes": [],
            "mealplans": [],
        }
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
            return Path(self.path).stem
        else:
            return "New cookbook"

    def add_metric(self, metric: str) -> bool:
        metric = metric.strip()
        if metric == "" or metric in self.metrics:
            return False
        self.metrics.append(metric)
        return True

    def rename_metric(self, index: int, new: str) -> bool:
        new = new.strip()
        if new == "" or new in self.metrics:
            return False
        old = self.metrics[index]
        self.metrics[index] = new
        for ing in self.ingredients:
            if old in ing.metrics:
                ing.metrics[new] = ing.metrics.pop(old)
        return True

    def delete_metric(self, index: int, view: Optional[QWidget] = None) -> bool:
        metric = self.metrics[index]
        used = any(ing.get_metric(metric) != 0 for ing in self.ingredients)
        if (
            used
            and view
            and not ask_confirmation(
                view,
                f"Remove the metric '{metric}'? Its values will be deleted from all ingredients.",
                "Remove",
            )
        ):
            return False
        del self.metrics[index]
        for ing in self.ingredients:
            ing.metrics.pop(metric, None)
        return True

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

    def delete_ingredient(self, index: int, view: Optional[QWidget] = None) -> None:
        ing = self.ingredients[index]
        if can_delete_component(ing, view) and confirm_delete(
            "ingredient", ing.display_name(), view
        ):
            del self.ingredients[index]
            del self._components[ing._id]

    def delete_recipe(self, index: int, view: Optional[QWidget] = None) -> None:
        recipe = self.recipes[index]
        if not can_delete_component(recipe, view) or not confirm_delete(
            "recipe", recipe.display_name(), view
        ):
            return
        if recipe.window != None:
            recipe.window.deleteLater()
            recipe.window = None
        for component, _ in recipe.amounts:
            self.unlink_component(recipe, component)
        del self.recipes[index]
        del self._components[recipe._id]

    def delete_mealplan(self, index: int, view: Optional[QWidget] = None) -> None:
        mealplan = self.mealplans[index]
        if not confirm_delete("meal plan", mealplan.display_name(), view):
            return
        mealplan._clear()
        del self.mealplans[index]

    def link_component(
        self, origin: Union[Recipe, Mealplan], name_id: str
    ) -> Optional[Union[Ingredient, Recipe]]:
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

    def unlink_component(
        self, origin: Union[Recipe, Mealplan], old: Union[Ingredient, Recipe]
    ) -> None:
        old._used[origin] -= 1
        if old._used[origin] == 0:
            del old._used[origin]

    def change_link(
        self,
        origin: Union[Recipe, Mealplan],
        old: Union[Ingredient, Recipe],
        new_id: str,
    ) -> Optional[Union[Ingredient, Recipe]]:
        new = self.link_component(origin, new_id)
        if new:
            self.unlink_component(origin, old)
            return new
        return None

    def add_entry(
        self,
        origin: Union[Recipe, Mealplan],
        entries: list[list[Any]],
        component_id: str,
        amount: Numeric = Decimal(0),
        strict: bool = False,
    ) -> bool:
        value = parse_amount(amount, strict)
        if value is None:
            return False
        component = self.link_component(origin, component_id)
        if component is None:
            if strict:
                raise ValueError("invalid component ID")
            return False
        entries.append([component, value])
        return True

    def change_entry(
        self,
        origin: Union[Recipe, Mealplan],
        entries: list[list[Any]],
        index: int,
        component_id: Optional[str] = None,
        amount: Optional[Numeric] = None,
        strict: bool = False,
    ) -> bool:
        value = None if amount is None else parse_amount(amount, strict)
        if amount is not None and value is None:
            return False
        if component_id is not None:
            component = self.change_link(origin, entries[index][0], component_id)
            if component is None:
                if strict:
                    raise ValueError("invalid component ID")
                return False
            entries[index][0] = component
        if value is not None:
            entries[index][1] = value
        return True

    def remove_entry(
        self, origin: Union[Recipe, Mealplan], entries: list[list[Any]], index: int
    ) -> None:
        self.unlink_component(origin, entries[index][0])
        del entries[index]

    def is_empty(self) -> bool:
        return len(self._components) == 0
