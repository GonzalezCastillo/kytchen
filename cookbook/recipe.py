import math
import json
import csv

from cookbook.ingredient import *

# Recipe steps.

def display_mins(t):
	minutes = math.floor(t / 60)
	seconds = t % 60
	return (minutes, seconds)

class Step():
	
	def __init__(self, description, minutes, seconds):
		self.description = description
		self.seconds = minutes * 60 + seconds
	
	def __str__(self):
		mins, secs = display_mins(self.seconds)
		return f"{self.description} ({mins}:{secs})"

# Recipes.

class Recipe:

	unit = "serv"

	def __init__(self, js):

		data = json.loads(js)
		self.name = data["name"]
		self.date = data["date"]
		self.amounts = {}
		self.steps = []
		
		for entry in data["ingredients"]:
			component = find_component(entry[0])
			amount = entry[1]
			self.amounts[component] = amount

		for step in data["method"]:
			self.steps.append(Step(step[0], step[1], step[2]))

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
		return math.ceil(total_seconds / 60)

	def console_string(self, servings = 1):
		string = f"""
{self.name} ({self.date})
Servings: {servings}
Calories: {math.ceil(self.get_calories(servings))} kcal
Preparation time: {self.get_minutes()} min

INGREDIENTS
"""
		amounts = self.get_amounts(servings)
		for ingredient in amounts:
			string += f"{amounts[ingredient]} {ingredient.unit}  {ingredient.name}\n"

		string += "\nMETHOD\n"
		total_secs = 0
		for step in self.steps:
			total_secs += step.seconds
			tot_mins, tot_secs = display_mins(total_secs)
			string += f"- {step.description} >{tot_mins}:{tot_secs}\n"
		return string

	def render_tex(self, servings = 1):
		return

	def print(self, servings = 1):
		print(self.console_string(servings))

	def __str__(self):
		return self.console_string(servings = 1)

recipes = {}

def load_recipes():
	global components
	global recipes
	with open("recipes.csv", "r") as f:
		for line in csv.reader(f):
			id_name = line[0]
			with open(f"recipes/{id_name}.json", "r") as rfile:
				data = rfile.read()
				recipe = Recipe(data)
				components[id_name] = recipe
				recipes[id_name] = recipe

load_recipes()
