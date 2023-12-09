import statistics
import math
import os

from kytchen.recipe import *

def number_subrecipes(recipe):
	num = 1
	for component in recipe.amounts:
		if type(component) == Recipe:
			num += number_subrecipes(component)
	return num

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

	sortkey = lambda item: -number_subrecipes(item[0])
	return dict(sorted(amounts.items(), key = sortkey))
	
def add_ingredients(dic, recipe, servings):
	for component in recipe.amounts:
		if type(component) == Recipe:
			add_ingredients(dic, component, servings)
		else:
			if not component in dic:
				dic[component] = 0
			dic[component] += recipe.amounts[component] * servings

def purge_dictionary(dic):
	rm = []
	for entry in dic:
		if dic[entry] == 0:
			rm.append(entry)
	for entry in rm:
		dic.pop(entry)


class MealPlan:
	def set_prepare(self, prepare):
		self._extra_prepare = prepare
		self._prepare = []
		if len(prepare) != len(self.consume):
			raise Exception("Incompatible prepare and consume lists")
			return

		done = {}
		for i, extra in enumerate(prepare):
			this_prepare = get_day_prepare(self.consume[i])
			for recipe in this_prepare:
				if recipe in done:
					amount_done = min(done[recipe], this_prepare[recipe])
					done[recipe] -= amount_done
					all_amounts_done = {}
					expand_recipe(all_amounts_done, recipe, amount_done)
					for component in all_amounts_done:
						this_prepare[component] -= all_amounts_done[component]
			for entry in extra:
				recipe = find_component(entry)
				if not recipe in done:
					done[recipe] = 0
				done[recipe] += extra[entry]

				all_amounts_do = {}
				expand_recipe(all_amounts_do, recipe, extra[entry])
				
				for component in all_amounts_do:
					if not recipe in this_prepare:
						this_prepare[component] = 0
					this_prepare[component] += all_amounts_do[component]

			purge_dictionary(this_prepare)
			purge_dictionary(done)
			self._prepare.append(this_prepare)

		self._excedent = done

	def __init__(self, consume, prepare, name = "", date = ""):

		self.name = name
		self.date = date
		self.consume = []
	
		for day in consume:
			parsed_day = {}	
			for recipe in day:
				parsed_day[find_component(recipe)] = day[recipe]
			self.consume.append(parsed_day)

		self.set_prepare(prepare)

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
		for day in self.consume:
			for meal in day:
				add_ingredients(ingredients, meal, day[meal])
		return ingredients

	def get_excedent(self):
		return self._excedent

	def __str__(self):
		string = ""
		for i, day in enumerate(self.consume):
			string += f"Day {i + 1}\nCONSUME:\n"
			for meal in day:
				string += f"- {meal.name} (servings: {day[meal]}, {math.ceil(meal.get_calories() * day[meal])} kcal)\n"
			string += "PREPARE:\n"
			for recipe in self._prepare[i]:
				string += f"- {recipe.name} (servings: {self._prepare[i][recipe]})\n"
			string += "\n"
		string += f"Average daily energy: {math.ceil(statistics.mean(self.get_calories()))} kcal\n"
		if len(self._excedent) != 0:
			string += "\n EXCEDENT:\n"
			for element in self._excedent:
				string += f"{self._excedent[element]} {element.name}\n"
		return string

	def shopping_list(self):
		string = "";
		ingredients = self.get_ingredients()
		for ing in ingredients:
			string += f"{ing.name}: {ingredients[ing]} {ing.unit}\n"
		return string
	
	def save(self, path):
		struct = {}
		struct["name"] = self.name
		struct["date"] = self.date
		struct["consume"] = []
		struct["prepare"] = []
		for i in range(len(self.consume)):
			struct["consume"].append(readable_amounts(self.consume[i]))
			struct["prepare"].append(readable_amounts(self._extra_prepare[i]))

		if not os.path.exists("mealplans"):
			os.mkdir("mealplans")

		js = json.dumps(struct)
		with open("mealplans/" + path + ".json", "w") as f:
			f.write(js)



def parse_mealplan(js):
	data = json.loads(js)
	consume = data["consume"]
	prepare = data["prepare"]
	name = data["name"]
	date = ""
	if "date" in data:
		date = data["date"]
	return MealPlan(consume, prepare, name, date)


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
