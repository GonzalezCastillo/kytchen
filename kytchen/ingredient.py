from decimal import Decimal
from .views import SortTableModel, SortTable, create_new, num

class Ingredient():
    def __init__(self, id_name, name = "", calories = Decimal(0), unit = ""):
        self.name = name
        self.calories = calories
        self.unit = unit
        self._used = {}
        self._id = id_name
    
    def export(self):
        data = {}
        data["name"] = self.name
        data["calories"] = str(self.calories)
        data["unit"] = self.unit
        data["id"] = self._id
        return data

    @classmethod
    def load(cls, data):
        return cls(data["id"], data["name"], Decimal(data["calories"]), data["unit"])

    def get_calories(self):
        return self.calories

    def __str__(self):
        return f"{self.name} ({self.calories} kcal/{self.unit})"
    
    def __repr__(self):
        return self.__str__()

    def _col(self, col, string = True):
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

    def get_ingredients(self, amount):
        return {self: amount}



class IngredientModel(SortTableModel):
    header_names = ["ID", "Ingredient", "kcal/unit", "Unit"]
    align = ["", "left", "", ""]

    def __init__(self, parent, cookbook):
        self.cookbook = cookbook
        super().__init__(parent, cookbook.ingredients)

    def get_data(self, row, col):
        ing = self.content[row]
        return ing._col(col)


    def set_data(self, row, col, value):
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

    def new_entry(self):
        def create_function(new_id):
            ing = Ingredient(new_id)
            return self.cookbook.register_ingredient(ing)
        create_new(self.parent(), "ingredient", create_function)
    
    def delete_entry(self, row):
        self.cookbook.delete_ingredient(row, self.parent())

 
class IngredientTable(SortTable):
    ModelClass = IngredientModel
    item_name = "ingredient"
    default_widths = [(0, 150), (2, 100), (3, 100)]
    fixed_widths = [2, 3]
    stretch_widths = [1]



