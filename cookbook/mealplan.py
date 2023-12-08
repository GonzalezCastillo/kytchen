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
		expand_recipe(amounts, item, recipes[item])
	return amounts

def add_ingredients(dic, recipe, servings):
	for component in recipe.amounts:
		if type(component) == Recipe:
			add_ingredients(dic, recipe, servings)
		else:
			if not component in dic:
				dic[component] = 0
			dic[component] += recipe[component] * servings

def purge_dictionary(dic):
	for entry in dic:
		if dic[entry] == 0:
			dic.pop(entry)

class MealPlan:
	def compute_prepare(self):
		prepare = self.prepare
		done = {}
		for i, day in enumerate(prepare):
			this_prepare = get_day_prepare(self.consume[i])
			for element in done:
				if element in this_prepare:
					amount_done = min(done[element], this_prepare[element])
					done[element] -= amount_done
					this_prepare[element] -= amount_done
			for entry in day:
				element = find_component(entry)
				if not entry in this_prepare:
					prepare[element] = 0
				this_prepare[element] += day[entry]
				done[element] += day[entry]

			purge_dictionary(this_prepare)
			purge_dictionary(done)
			self.prepare.append(this_prepare)

		self.excedent = done

	def __init__(self, consume, prepare, name = "", date = ""):

		self.name = name
		self.date = date
		self.consume = []
		self.prepare = prepare
		
		for day in consume:
			parsed_day = {}	
			for recipe in day:
				parsed_day[find_compomemt(recipe)] = day[recipe]
			self.consume.append(parsed_day)

		self.compute_prepare()

	def get_calories(self):
		calories = []
		for day in self.consume:
			total = 0
			for meal in day:
				total += meal.get_calories() * day[meal]
			calories.append(total)
		return calories 

	def get_ingredients(self):
		ingredients = {}
		for day in self.comsume:
			for meal in day:
				add_ingredients(ingredients, meal, day[meal])
		return ingredients

	def get_excedent(self):
		self.compute_prepare()
		return self.excedent

	def __str__(self):
		self.compute_prepare()
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
		if len(self.excedent) != 0:
			string += "\n EXCEDENT:\n"
			for element in self.excedent:
				string += f"{self.excedent[element]} {element.name}\n"
		return string

	def shopping_list(self):
		string = "";
		ingredients = self.get_ingredients()
		for ing in ingredients:
			string += f"{ing.name}: {ingredients[ing]} {ing.unit}\n"
		return string

def parse_mealplan(js):
	data = json.loads(js)
	consume = data["consume"]
	prepare = data["prepare"]
	name = data["name"]
	date = ""
	if "date" in data:
		date = data["date"]
	return Mealplan(consume, prepare, name, date)


mealplans = {}

def load_mealplans():
	global mealplans
	if not os.path.isdir("mealplans"):
		return
	for file in os.listdir("mealplans"):
		if not file.endswith(".json"):
			continue
		with open(f"mealplans/{file}", "r") as rfile:
			data = rfile.read()
			mealplan = parse_mealplan(data) 
			mealplans[mealplan.name] = mealplan

load_mealplans()
