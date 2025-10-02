import math

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QInputDialog, QWidget, QHBoxLayout, QVBoxLayout, QPushButton
)
from decimal import Decimal

from .views import (
    DashboardTable, DashboardTableModel, CoreTableModel, FixTable,
    create_new, num, Title, Subtitle, general_margin, no_margin
)


def time_string(t):
    if t < 0:
        raise ValueError("cannot time travel")
    hours = math.floor(t / 3600)
    t = t % 3600
    minutes = math.floor(t / 60)
    seconds = t % 60
    time = ""
    if hours != 0:
        time += f"{hours}:"
    time += f"{minutes}:{seconds}"
    return time

def parse_time(time):
    chunks = time.split(':')
    if len(chunks) == 1:
        return int(chunks[0]) * 60
    elif len(chunks) == 2:
        return int(chunks[0]) * 60 + int(chunks[1])
    elif len(chunks) == 3:
        return int(chunks[0]) * 3600 + int(chunks[1]) * 60 + int(chunks[2])
    else:
        raise ValueError("invalid time format")

class Step():
    def __init__(self, description, seconds):
        self.description = description
        self.seconds = seconds
    
    def __str__(self):
        if self.seconds != math.nan:
            return f"{self.description} ({time_string(self.seconds)})"
        else:
            return self.description

class Recipe:
    unit = "serv"
    def __init__(self, id_name, cookbook, name = "", category = "", steps = None):
        self.name = name
        if steps == None:
            steps = []
        self.steps = steps
        self.category = category

        self.cookbook = cookbook
        self.amounts = []
        self._id = id_name
        self._used = {}
        self.window = None

    def export(self):
        data = {"name": self.name, "category": self.category, "id": self._id}
        steps = []
        for step in self.steps:
            steps.append([step.description, step.seconds]) 
        amounts = []
        for component, amount in self.amounts:
            amounts.append([component._id, str(amount)])

        data["steps"] = steps
        data["amounts"] = amounts

        return data 

    @classmethod
    def load_steps(cls, data, cookbook):
        id_name = data["id"]
        name = data["name"]
        category = data["category"]
        steps = []
        for step in data["steps"]:
            steps.append(Step(step[0], step[1]))
        return cls(id_name, cookbook, name, category, steps)
    
    def load_amounts(self, data):
        data = data["amounts"]
        for entry in data:
            self.new_component(entry[0], entry[1], True)

    def change_amounts(self, index, component = None, amount = None, strict = False):
        if component != None:
            ing, _ = self.amounts[index]
            new = self.cookbook.change_link(self, ing, component)
            if new == None:
                if strict:
                    raise ValueError("invalid component ID")
                return False
            self.amounts[index][0] = new
        if amount != None:
            try:
                value = num(amount)
            except:
                if strict:
                    raise ValueError("invalid amount")
                return False
            self.amounts[index][1] = value 
        return True

    def new_component(self, id_name, amount = Decimal(0), strict = False):
        new = self.cookbook.link_component(self, id_name)
        if new != None:
            self.amounts.append([new, num(amount)])
            return True
        elif strict:
            raise ValueError("invalid component ID")
        else:
            return False

    def get_amounts(self, servings = 1):
        amounts = []
        for (component, amount) in self.amounts:
            amounts.append((component, amount * servings))
        return amounts

    def get_calories(self, servings = 1):
        calories = 0
        amounts = self.get_amounts(servings)
        for (component, amount) in amounts:
            calories += amount * component.get_calories()
        return calories

    def get_seconds(self):
        total_seconds = 0
        for step in self.steps:
            total_seconds += step.seconds
        return total_seconds

    def get_time(self):
        return time_string(self.get_seconds())

    def recipe_string(self, servings = 1):
        string = self.name
        string += f"""
Servings: {servings}
Calories: {math.ceil(self.get_calories(servings))} kcal
"""
        time = time_string(self.get_seconds())
        string += f"Preparation time: {time}\n"

        string += "\nINGREDIENTS\n"
        amounts = self.get_amounts(servings)
        for ingredient, amount in amounts:
            string += f"{amount} {ingredient.unit}  {ingredient.name}\n"

        string += "\nMETHOD"
        tot_seconds = 0
        for step in self.steps:
            string += f"\n- {step.description} ({time_string(step.seconds)})"
            tot_seconds += step.seconds
            string += " >{time_string(tot_seconds)}"
        return string

    def __str__(self):
        return self.recipe_string(servings = 1)
    
    def __repr__(self):
        return f"{self.name} ({math.ceil(self.get_calories(1))} kcal/serv)"

    def _col(self, col):
        if col == 0:
            return self._id
        elif col == 1:
            return self.name
        elif col == 2:
            return self.category
        elif col == 3:
            return str(self.get_calories())
        elif col == 4:
            return self.get_time()
        else:
            return None

    def get_ingredients(self, servings):
        total = {}
        for component, amount in self.amounts:
            add = component.get_ingredients(amount * servings)
            for c, a in add:
                if c in total:
                    total[c] += a
                else:
                    total[c] = a
        return total

    def get_window(self):
        if self.window == None:
            self.window = RecipeView(self, self.cookbook.window)
        else:
            self.window.refresh()
        self.window.set_editing(False)
        self.window.show()


class RecipeDashModel(DashboardTableModel):
    header_names = ["ID", "Recipe name", "Category", "kcal", "Prep. time", ""]
    align = ["", "left", "", "", "", "", ""]
    not_editable = [3, 4, 5]

    def __init__(self, parent, cookbook):
        self.cookbook = cookbook
        super().__init__(parent, cookbook.recipes)

    def get_data(self, row, col):
        recipe = self.content[row]
        return recipe._col(col)


    def set_data(self, row, col, value):
        recipe = self.content[row]
        if col == 0:
            self.cookbook.update_component_id(recipe, value) 
        elif col == 1:
            recipe.name = value
            if recipe.window != None:
                recipe.window.refresh_name()
        elif col == 2:
            recipe.category = value

        return True       

    def new_entry(self):
        def create_function(new_id):
            rec = Recipe(new_id, self.cookbook)
            return self.cookbook.register_recipe(rec)
        create_new(self.parent(), "recipe", create_function)
    
    def delete_entry(self, row):
        self.cookbook.delete_recipe(row, self.parent()) 

 
class RecipeDashTable(DashboardTable):
    ModelClass = RecipeDashModel 
    item_name = "recipe"
    default_widths = [(0, 150), (2, 150), (3, 100), (4, 100)]
    fixed_widths = [3, 4]
    stretch_widths = [1]



class RecipeView(QWidget):
    def __init__(self, recipe, parent):
        super().__init__(parent = parent)
        self.setWindowFlag(Qt.WindowType.Window)
        self.resize(500, 700)
        self.recipe = recipe

        self.layout = QVBoxLayout()
        self.layout.setSpacing(0)
        no_margin(self.layout)
        self.heading = QVBoxLayout()
        general_margin(self.heading)
        self.setLayout(self.layout)

        hbox = QHBoxLayout()
        self.name_label = Title("")
        self.kcal_label = Title("")
        self.time_label = Subtitle("")
        hbox.addWidget(self.name_label)
        hbox.addStretch(1)
        hbox.addWidget(self.kcal_label)
        self.heading.addLayout(hbox)
        self.heading.addWidget(self.time_label)
        self.layout.addLayout(self.heading)

        self.refresh_name()

        self.amounts_table = AmountsTable(self.recipe)
        self.amounts_table.model.refresh.connect(self.refresh)
        self.layout.addWidget(self.amounts_table)

        self.steps_table = StepsTable(self.recipe.steps)
        self.steps_table.model.refresh.connect(self.refresh)
        self.layout.addWidget(self.steps_table)

        self.controls = QHBoxLayout()
        self.controls.setContentsMargins(15,15,15,15)
        self.edit_button = QPushButton("")
        self.edit_button.clicked.connect(self.toggle_edit)
        self.set_editing(False)

        self.controls.addStretch()
        self.controls.addWidget(self.edit_button)

        self.layout.addLayout(self.controls)
        self.refresh()

    def set_editing(self, edit):
        self.editing = edit
        if edit:
            self.edit_button.setText("Save")
        else:
            self.edit_button.setText("Edit")
        self.steps_table.set_editable(edit)
        self.amounts_table.set_editable(edit)

    def toggle_edit(self):
        self.set_editing(not self.editing)

    def refresh(self):
        self.kcal_label.setText(f"{self.recipe.get_calories()} kcal")
        self.time_label.setText(f"Preparation time {self.recipe.get_time()}")

    def refresh_name(self):
        self.setWindowTitle(f"Recipe '{self.recipe.name}'")
        self.name_label.setText(self.recipe.name)

class StepsTableModel(CoreTableModel):
    header_names = ["Step", "Duration", "End time"]
    align = ["left", "", ""]
    refresh = pyqtSignal()

    def sum_seconds(self, row):
        return sum([st.seconds for st in self.content[:row+1]])

    def get_data(self, row, col):
        step = self.content[row]
        if col == 0:
            return step.description
        elif col == 1:
            return time_string(step.seconds)
        elif col == 2:
            return time_string(self.sum_seconds(row))
   
    def set_data(self, row, col, value):
        step = self.content[row]
        if col == 0:
            step.description = value
            return True
        try:
            value = parse_time(value)
        except:
            return False
        if col == 1:
            step.seconds = value
        elif col == 2:
            seconds = value - self.sum_seconds(row) + step.seconds
            if seconds >= 0:
                step.seconds = seconds
            else:
                return False
        self.refresh.emit()
        self.update_row(row)
        self.update_col(2)

        return True

    def new_entry(self):
        self.content.append(Step("", 0))

    def dolete_entry(self, row):
        del self.content[row]

class StepsTable(FixTable):
    ModelClass = StepsTableModel
    item_name = "step"
    default_widths = [(1,100), (2,100)]
    fixed_widths = [1,2]
    stretch_widths = [0]


class AmountsTableModel(CoreTableModel):
    header_names = ["Ingredient", "Amount"]
    align = ["right", ""]
    refresh = pyqtSignal()

    def __init__(self, parent, recipe):
        self.recipe = recipe
        self.cookbook = recipe.cookbook
        super().__init__(parent, recipe.amounts)

    def deep_data(self, row, col, is_display):
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
   
    def set_data(self, row, col, value):
        if col == 0:
            self.recipe.change_amounts(row, component = value)
        elif col == 1:
            self.recipe.change_amounts(row, amount = value)
        else:
            return False

        self.refresh.emit()
        return True

    def new_entry(self):
        new_id, ok = QInputDialog.getText(self.parent(), "New ingredient",
            "Please specify the name of an ingredient or recipe:")
        self.recipe.new_component(new_id) 

    def dolete_entry(self, row):
        component = self.content[row][0]
        self.cookbook.unlink_component(self.recipe, component)
        del self.content[row]

class AmountsTable(FixTable):
    ModelClass = AmountsTableModel
    item_name = "ingredient"
    default_widths = [(1,100),]
    fixed_widths = [1]
    stretch_widths = [0]
