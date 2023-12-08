import csv
import os

components = {}

class Ingredient():
	def __init__(self, name, calories, unit):
		self.name = name
		self.calories = calories
		self.unit = unit
		self.id_name = ""
		self.kept = False
	
	def keep(self, id_name ):
		if self.kept:
			raise Exception("This ingredient has already been kept", self)
			return
		else:
			self.kept = True
		self.id_name = id_name
		global components
		components[id_name] = self

	def get_calories(self):
		return self.calories

	def __str__(self):
		return f"{self.name} ({self.calories} kcal/{self.unit})"


def load_ingredients():
	global components
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
			ing.keep(id_name)


load_ingredients()

