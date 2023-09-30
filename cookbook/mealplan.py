import statistics
import math
import os

from cookbook.recipe import *

def expand_recipe(dic, recipe, servings):
	if not recipe in dic:
		dic[recipe] = 0
	dic[recipe] += servings
	for component in recipe.amounts:
		if type(component) == Recipe:
			expand_recipe(dic, component, servings * recipe.amounts[component])
	return dic

def get_day_prepare(recipes):
	amounts = {}
	for item in recipes:
		expand_recipe(amounts, item, find_component(item))
	return amounts

class MealPlan:
	def __init__(self, js):

		data = json.loads(js)
		self.name = data["name"]
		self.date = data["date"]
		self.consume = []
		self.prepare = []
		
		for day in data["consume"]:
			consume = {}
			for entry in day:
				recipe = find_component[entry[0]]
				amount = entry[1]
				consume[recipe] = amount
			self.consume.append(consume)

		done = {}
		for i, day in enumerate(data["prepare"]):
			prepare = get_day_prepare(self.consume[i])
			rm = []
			for element in done:
				if element in prepare:
					done[element][element] += prepare[element]
					rm.append(element)
					prepare.pop(element)
			for element in rm:
				done.pop(element)
			for entry in day:
				element = find_component[entry]
				if not entry in prepare:
					prepare[element] = 0
				done[element] = prepare
			self.prepare.append(prepare)
				

	def get_calories(self):
		calories = []
		for day in self.consume:
			total = 0
			for meal in day:
				total += meal.get_calories() * day[meal]
			calories.append(total)
		return calories 

	def __str__(self):
		string = ""
		for i, day in enumerate(self.consume):
			string += f"Day {i}\nCONSUME:\n"
			for meal in day:
				string += f"- {meal.name} (servings: {day[meal]}, {math.ceil(meal.get_calories() * day[meal])} kcal)\n"
			string += "PREPARE:\n"
			for recipe in self.prepare[i]:
				string += f"- {recipe.name} (servings: {self.prepare[i][recipe]})\n"
			string += "\n"
		string += f"Average daily energy: {math.ceil(statistics.mean(self.get_calories()))} kcal\n"
		return string

mealplans = {}

def load_mealplans():
	global mealplans
	for file in os.listdir("mealplans"):
		if not file.endswith(".json"):
			continue
		with open(f"mealplans/{file}", "r") as rfile:
			data = rfile.read()
			mealplan = MealPlan(data)
			mealplans[mealplan.name] = mealplan

load_mealplans()
