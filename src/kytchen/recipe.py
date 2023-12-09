import math
import json
import csv
import os

from kytchen.ingredient import *

# Recipe steps.

def display_mins(t):
	minutes = math.floor(t / 60)
	seconds = t % 60
	return (minutes, seconds)

class Step():
	
	def __init__(self, description, seconds):
		self.description = description
		self.seconds = seconds
	
	def __str__(self):
		if self.seconds != math.nan:
			mins, secs = display_mins(self.seconds)
			return f"{self.description} ({mins}:{secs})"
			return self.description

def process_step(raw_step):
	
	if type(raw_step) == str:
		return Step(raw_step, math.nan)

	desc = raw_step[0]
	time = raw_step[1]
	if type(time) == list:
		time = 60 * time[0] + time[1]
	else:
		time = 60 * time
	
	return Step(desc, time)

def readable_amounts(amounts):
	new_amounts = {}
	for component in amounts:
		if type(component) == str:
			new_amounts[component] = amounts[component]
		elif component.id_name == "":
			raise Exception("All components must be kept")
			return None
		else:
			new_amounts[component.id_name] = amounts[component]
	return new_amounts


# Recipes.

class Recipe:

	unit = "serv"

	def __init__(self, ingredients, method = [], name = "", date = ""):
		self.name = name
		self.date = date
		self.amounts = {}
		self.steps = []
		self.id_name = "_"
		self.kept = False

		for entry in ingredients:
			if type(entry) == str:
				self.amounts[find_component(entry)] = ingredients[entry]
			elif type(entry) == Ingredient:
				self.amounts[entry] = ingredients[entry]
			else:
				raise TypeError("Invalid ingredient", entry)
		
		for step in method:
			self.steps.append(process_step(step))

	def keep(self, id_name):
		if self.kept:
			raise Exception("This ingredient has already been kept", self)
			return
		else:
			self.kept = True

		global components
		self.id_name = id_name
		components[id_name] = self

	def save(self, path = ""):
		if path == "":
			path = self.id_name

		components[path] = self	

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

		struct["method"] = steps
		struct["ingredients"] = readable_amounts(self.amounts)

		if not os.path.exists("recipes"):
			os.mkdir("recipes")
	
		js = json.dumps(struct)
		with open("recipes/" + path + ".json", "w") as f:
			f.write(js)


	def get_amounts(self, servings = 1):
		amounts = {}
		for component in self.amounts:
			amounts[component] = self.amounts[component] * servings
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

		string += "\nMETHOD\n"
		total_secs = 0
		for step in self.steps:
			if not math.isnan(mins):
				total_secs += step.seconds
				tot_mins, tot_secs = display_mins(total_secs)
				string += f"- {step.description} >{tot_mins}:{tot_secs}\n"
			elif not math.isnan(step.seconds):
				add_mins, add_secs = display_mins(step.seconds)
				string += f"- {step.description} +{add_mins}:{add_secs}\n"
			else:
				string += f"- {step.description}\n"
		return string

	def print(self, servings = 1):
		print(self.recipe_string(servings))

	def __str__(self):
		return self.recipe_string(servings = 1)

def parse_recipe(js):
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

def get_recipe(name):
	global components
	if name not in components:
		with open(f"recipes/{name}.json", "r") as rfile:
			data = rfile.read()
			recipe = parse_recipe(data)
			recipe.keep(name)
	return components[name]

def find_component(name):
	if type(name) != str:
		return name
	
	global components
	if name in components:
		return components[name]
	else:
		return get_recipe(name)
