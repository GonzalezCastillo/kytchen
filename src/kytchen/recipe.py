import math
import json
import csv
import os

from kytchen.ingredient import *
from kytchen.ingredient import _components

# Recipe steps.

def _display_mins(t):
	minutes = math.floor(t / 60)
	seconds = t % 60
	return (minutes, seconds)


class Step():
	def __init__(self, description, seconds):
		self.description = description
		self.seconds = seconds
	
	def __str__(self):
		if self.seconds != math.nan:
			mins, secs = _display_mins(self.seconds)
			return f"{self.description} ({mins}:{secs})"
		else:
			return self.description


def process_step(raw_step):
	"""Creates a step object.
- If given a string, creates a step with the string as description.
- If given a list [str, min], creates a step with:
	- description: str
	- seconds: 60 * min
- If given a list [str, [min, sec]], creates a step with:
	- description: str
	- seconds: 60 * min + sec
"""
	if type(raw_step) == str:
		return Step(raw_step, math.nan)

	desc = raw_step[0]
	time = raw_step[1]
	if type(time) == list:
		time = 60 * time[0] + time[1]
	else:
		time = 60 * time
	
	return Step(desc, time)


# Recipes.

class Recipe:

	unit = "serv"

	def __init__(self, ingredients, method = [], name = "Unnamed recipe", date = ""):
		"""Initialises a Recipe object with the following arguments:
- ingredients: A dictionary specifying the components of the recipe,
	- keys are IDs or paths of ingredients or recipes,
	- and values are the amounts needed.
- method: A list of steps, specified as in the input to process_step.
- name: Optional name of the recipe.
- date: Optional date of creation of the recipe.
"""
		self.name = name
		self.date = date
		self.amounts = {}
		self.steps = []
		self.id_name = ""

		for entry in ingredients:
			if find_component(entry) == None:
				raise TypeError("Invalid ingredient", entry)
			else:
				self.amounts[entry] = ingredients[entry]
		
		for step in method:
			self.steps.append(process_step(step))

	def _keep(self, id_name):
		if type(id_name) != str or id_name == "":
			raise Exception("Invalid recipe ID", id_name)
		if self.id_name != "" and self.id_name != id_name:
			raise Exception("A recipe cannot have two paths/IDs", self)

		global _components
		self.id_name = id_name
		_components[id_name] = self

	def save(self, path = ""):
		"""Saves the recipe in the file "recipes/{path}.json".
A path must be specified if the recipe hasn't been saved yet.
If it had been saved before, the path must be the same (or dropped).
When a recipe is saved, it can be reached with find_component.
"""
		if path == "" and self.id_name == "":
			raise Exception("A path must be provided", self)
		elif path != "":
			self._keep(path)
		
		path = self.id_name

		struct = {"name": self.name, "date": self.date}
		steps = []
		for step in self.steps:
			if math.isnan(step.seconds):
				steps.append(step.description)
			elif step.seconds % 60 == 0:
				steps.append([step.description, step.seconds/60])
			else:
				mins = math.floor(step.seconds / 60)
				secs = step.seconds % 60
				steps.append([step.description, [mins, secs]])

		struct["ingredients"] = self.amounts
		if steps != []:
			struct["method"] = steps

		if not os.path.exists("recipes"):
			os.mkdir("recipes")
	
		js = json.dumps(struct, indent = '\t')
		with open("recipes/" + path + ".json", "w") as f:
			f.write(js)


	def get_amounts(self, servings = 1):
		amounts = {}
		for component in self.amounts:
			obj = find_component(component)
			if obj == None:
				raise Exception("Corrupted ingredient", component)
			amounts[obj] = self.amounts[component] * servings

		return amounts

	def get_calories(self, servings = 1):
		calories = 0
		amounts = self.get_amounts(servings)
		for component in amounts:
			calories += amounts[component] * component.get_calories()
		return calories

	def get_minutes(self):
		total_seconds = 0
		for step in self.steps:
			total_seconds += step.seconds
		if not math.isnan(total_seconds):
			return math.ceil(total_seconds / 60)
		else:
			return math.nan

	def recipe_string(self, servings = 1):
		string = self.name
		if self.date != "":
			string += f" ({self.date})"
		string += f"""
Servings: {servings}
Calories: {math.ceil(self.get_calories(servings))} kcal
"""
		mins = self.get_minutes()
		if not math.isnan(mins) and mins != 0:
			string += f"Preparation time: {self.get_minutes()} min\n"

		string += "\nINGREDIENTS\n"
		amounts = self.get_amounts(servings)
		for ingredient in amounts:
			string += f"{amounts[ingredient]} {ingredient.unit}  {ingredient.name}\n"

		if self.steps != []:
			string += "\nMETHOD\n"
		total_secs = 0
		for step in self.steps:
			if not math.isnan(mins):
				total_secs += step.seconds
				tot_mins, tot_secs = _display_mins(total_secs)
				string += f"- {step.description} >{tot_mins}:{tot_secs}\n"
			elif not math.isnan(step.seconds):
				add_mins, add_secs = _display_mins(step.seconds)
				string += f"- {step.description} +{add_mins}:{add_secs}\n"
			else:
				string += f"- {step.description}\n"
		return string

	def print(self, servings = 1):
		print(self.recipe_string(servings))

	def __str__(self):
		return self.recipe_string(servings = 1)
	
	def __repr__(self):
		return f"{self.name} ({math.ceil(self.get_calories(1))} kcal/serv)"

def parse_recipe(js):
	"""Creates a Recipe object from a JSON representation.
"""
	data = json.loads(js)
	ingredients = data["ingredients"]	
	name = data["name"]
	date = ""
	if "date" in data:
		date = data["date"]
	method = []
	if "method" in data:
		method = data["method"]
	return Recipe(ingredients, method, name, date)

def _get_recipe(name):
	global _components
	with open(f"recipes/{name}.json", "r") as rfile:
		data = rfile.read()
		recipe = parse_recipe(data)
		recipe._keep(name)
	return _components[name]

def find_component(name):
	"""Looks for a saved component (recipe or ingredient).
In the case of ingredients, name must be the unique ID.
In the case of recipes, name must be the path to the recipe.
	"""
	global _components
	if name in _components:
		return _components[name]
	else:
		return _get_recipe(name)

def reload_recipes():
	"""Reloads all saved recipes.
"""
	global _components
	for item in _components:
		if type(_components[item]) == Recipe:
			_get_recipe(item)
