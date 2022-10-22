import csv

class Ingredient():
	unit = ""
	calories = 0
	name = ""

	def __init__(self, name, calories, unit):
		self.name = name
		self.calories = calories
		self.unit = unit

	def __str__(self):
		return f"{self.name} ({self.calories} kcal/{self.unit})"


ingredients_index = {}
def load_ingredients():
	global ingredients_index
	ingredients_index = {}
	with open("ingredients.csv", "r") as f:
		for line in csv.reader(f, delimiter = ";"):
			id_name = line[0]
			full_name = line[1]
			calories = float(line[2])
			unit = line[3]
			ingredients_index[id_name] = Ingredient(full_name, calories, unit)

def find_ingredient(id):
	return ingredients_index[id]

load_ingredients()

