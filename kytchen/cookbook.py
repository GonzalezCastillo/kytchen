import json
from decimal import Decimal

from .ingredient import Ingredient
from .recipe import Recipe
from .mealplan import Mealplan
from .views import show_error

def can_delete_component(component, view = None):
    if component._used:
        if view:
            used_name = list(component._used.keys())[0].name
            show_error(view,
                f"Cannot delete {component.name}. It is used in {used_name}.")
        return False
    else:
        return True

class Cookbook():
    def __init__(self):
        self._components = {}
        self.ingredients = []
        self.recipes = []
        self.mealplans = []
        self.path = None
        self.window = None

    @classmethod
    def load(cls, path):
        with open(path, "r") as f:
            data = json.load(f)
        self = cls()
        for ing in data["ingredients"]:
            ing = Ingredient.load(ing)
            self.register_ingredient(ing)
        for rec in data["recipes"]:
            rec = Recipe.load_steps(rec, self)
            self.register_recipe(rec)
        for rec in data["recipes"]:
            self._components[rec["id"]].load_amounts(rec)
        for plan in data["mealplans"]:
            plan = Mealplan.load(plan, self)
            self.register_mealplan(plan)
        self.path = path
        return self

    def save(self, path = None):
        data = {"ingredients": [], "recipes": [], "mealplans": []}
        for ing in self.ingredients:
            data["ingredients"].append(ing.export())
        for rec in self.recipes:
            data["recipes"].append(rec.export())
        for plan in self.mealplans:
            data["mealplans"].append(plan.export())
        if path == None:
            path = self.path
        with open(path, "w") as f:
            json.dump(data, f)

    def set_path(self, path):
        self.path = path

    def get_name(self):
        if self.path != None:
            return self.path.split("/")[-1].split("\\")[-1].strip(".js")
        else:
            return "New cookbook"

    def register_component(self, component):
        if component._id in self._components:
            return False
        self._components[component._id] = component
        return True

    def register_ingredient(self, ingredient):
        if self.register_component(ingredient):
            self.ingredients.append(ingredient)
            return True
        else:
            return False

    def register_recipe(self, recipe):
        if self.register_component(recipe):
            self.recipes.append(recipe)
            return True
        else:
            return False

    def register_mealplan(self, mealplan):
        self.mealplans.append(mealplan)

    def update_component_id(self, component, new):
        if new in self._components:
            return False
        self._components[new] = self._components.pop(component._id)
        component._id = new
        return True

    def delete_ingredient(self, index, view = None):
        ing = self.ingredients[index]
        if can_delete_component(ing, view):
            del self.ingredients[index]
            del self._components[ing._id]

    def delete_recipe(self, index, view = None):
        recipe = self.recipes[index]
        if recipe.window != None:
            recipe.window.deleteLater()
        for component, _ in recipe.amounts:
            self.unlink_component(recipe, component)
        if can_delete_component(recipe, view):
            del self.recipes[index]
            del self._components[recipe._id]

    def delete_mealplan(self, index):
        mealplan = self.mealplans[index]
        mealplan._clear()
        del self.mealplans[index]

    def link_component(self, origin, name_id):
        if name_id in self._components:
            obj = self._components[name_id]
            if obj == origin:
                return None
            obj._used.setdefault(origin, 0)
            obj._used[origin] += 1
            return obj
        else:
            return None

    def unlink_component(self, origin, old):
        old._used[origin] -= 1
        if old._used[origin] == 0:
            del old._used[origin]

    def change_link(self, origin, old, new_id):
        new = self.link_component(origin, new_id)
        if new:
            self.unlink_component(origin, old)
            return new
        return None

    def is_empty(self):
        return len(self._components) == 0
