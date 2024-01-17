import csv
import os

_components = {}
_ingredients = []

class Ingredient():
	def __init__(self, name, calories, unit):
		self.name = name
		self.calories = calories
		self.unit = unit
		self._id = ""
	
	def _keep(self, id_name):
		self._id = id_name
		global _components
		_components[id_name] = self
		if id_name not in _ingredients:
			_ingredients.append(id_name)

	def get_calories(self):
		return self.calories

	def __str__(self):
		return f"{self.name} ({self.calories} kcal/{self.unit})"
	
	def __repr__(self):
		return self.__str__()


def load_ingredients():
	"""Loads all the ingredients contained in the ingredients.csv file.
In this file, every row must represent an ingredient.
Within each row, each cell must specify:

1. A unique ID for the ingredient.
2. The full name of the ingredient.
3. The number of calories of the ingredient per unit of measurement.
4. The unit of measurement of the ingredient.

Once loaded, the ingredients can be accessed with find_components.
"""

	global _components
	global _ingredients

	for ing in _ingredients:
		_components.pop(ing)

	if not os.path.exists("ingredients.csv"):
		return

	with open("ingredients.csv", "r") as f:
		for line in csv.reader(f, delimiter = ";"):
			if line[0] == "":
				continue
			id_name = line[0]
			full_name = line[1]
			calories = float(line[2])
			unit = line[3]
			ing = Ingredient(full_name, calories, unit)
			ing._keep(id_name)


load_ingredients()

