import math
import csv

from cookbook.ingredient import *

# Recipe steps.

def display_mins(t):
	minutes = math.floor(t / 60)
	seconds = t & 60
	return (minutes, seconds)

class Step():
	description = ""
	seconds = 0

	def __init__(self, description, minutes, seconds):
		self.description = description
		self.seconds = minutes * 60 + seconds
	
	def __str__(self):
		mins, secs = display_mins(self.seconds)
		return f"{self.description} ({mins}:{secs})"

# Recipes.

class Recipe():
	name = ""
	date = ""
	amounts = {} # Dictionary of ingredient amounts indexed by ingredients.
	steps = [] 

	def __init__(self, where):
		where = "recipes/" + where
		with open(where, "r") as f:
			reader = csv.reader(f, delimiter = ";")
			
			line = next(reader)
			self.name = line[0]
			self.date = line[1]

			read_ingredient = True
			for line in reader:
				if (line[0] == "***"):
					read_ingredient = False
					continue	
				if (read_ingredient):
					ingredient = find_ingredient(line[0])
					amount = float(line[1])
					self.amounts[ingredient] = amount
				else:
					step = Step(line[0], int(line[1]), int(line[2]))
					self.steps.append(step)

	def get_calories(self):
		calories = 0
		for ingredient in self.amounts:
			calories += self.amounts[ingredient] * ingredient.calories
		return calories

	def get_minutes(self):
		total_seconds = 0
		for step in self.steps:
			total_seconds += step.seconds
		return math.floor(total_seconds / 60)

	def __str__(self):
		string = f"""
{self.name} ({self.date})
Calories: {self.get_calories()} kcal
Preparation time: {self.get_minutes()} min

INGREDIENTS
"""
		for ingredient in self.amounts:
			string += f"{self.amounts[ingredient]} {ingredient.name}\n"

		string += "\nMETHOD\n"
		total_secs = 0
		for step in self.steps:
			tot_mins, tot_secs = display_mins(total_secs)
			mins, secs = display_mins(step.seconds)
			string += f"{tot_mins}:{tot_secs} > "
			string += f"{step.description} ({mins}:{secs})\n"
			total_secs += step.seconds
			return string

	def render_tex(self):
		return

