import csv

class Ingredient():
	def __init__(self, name, calories, unit):
		self.name = name
		self.calories = calories
		self.unit = unit

	def get_calories(self):
		return self.calories

	def __str__(self):
		return f"{self.name} ({self.calories} kcal/{self.unit})"

components = {}

def load_ingredients():
	global components
	with open("ingredients.csv", "r") as f:
		for line in csv.reader(f, delimiter = ";"):
			if line[0] == "":
				continue
			id_name = line[0]
			full_name = line[1]
			calories = float(line[2])
			unit = line[3]
			components[id_name] = Ingredient(full_name, calories, unit)


load_ingredients()

