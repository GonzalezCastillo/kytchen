import statistics
import math
import os

from kytchen.recipe import *

def _number_subrecipes(recipe):
	num = 1
	for component in recipe.get_amounts():
		if type(component) == Recipe:
			num += _number_subrecipes(component)
	return num

def _expand_recipe(dct, recipe, servings):
	if not recipe in dct:
		dct[recipe] = 0
	dct[recipe] += servings
	amounts = recipe.get_amounts()
	for component in amounts:
		if type(component) == Recipe:
			_expand_recipe(dct, component, servings * amounts[component])
	return dct

def _get_day_prepare(recipes):
	amounts = {}
	for item in recipes:
		recipe = find_component(item)
		_expand_recipe(amounts, recipe, recipes[item])

	sortkey = lambda item: -_number_subrecipes(item[0])
	return dict(sorted(amounts.items(), key = sortkey))
	
def _add_ingredients(dct, recipe, servings):
	amounts = recipe.get_amounts()
	for component in amounts:
		if type(component) == Recipe:
			_add_ingredients(dct, component, servings)
		else:
			if not component in dct:
				dct[component] = 0
			dct[component] += amounts[component] * servings

def _purge_dictionary(dct):
	rm = []
	for entry in dct:
		if dct[entry] == 0:
			rm.append(entry)
	for entry in rm:
		dct.pop(entry)


class MealPlan:
	def set_prepare(self, prepare):
		"""This function is used to update "prepare", which is private.
"""
		self._extra_prepare = prepare
		self._prepare = []
		if len(prepare) != len(self.consume):
			raise Exception("Incompatible prepare and consume lists")
			return

		done = {}
		for i, extra in enumerate(prepare):
			this_prepare = _get_day_prepare(self.consume[i])
			for recipe in this_prepare:
				if recipe in done:
					amount_done = min(done[recipe], this_prepare[recipe])
					done[recipe] -= amount_done
					all_amounts_done = {}
					_expand_recipe(all_amounts_done, recipe, amount_done)
					for component in all_amounts_done:
						this_prepare[component] -= all_amounts_done[component]
			for entry in extra:
				recipe = find_component(entry)
				if not recipe in done:
					done[recipe] = 0
				done[recipe] += extra[entry]

				all_amounts_do = {}
				_expand_recipe(all_amounts_do, recipe, extra[entry])
				
				for component in all_amounts_do:
					if not recipe in this_prepare:
						this_prepare[component] = 0
					this_prepare[component] += all_amounts_do[component]

			_purge_dictionary(this_prepare)
			_purge_dictionary(done)
			self._prepare.append(this_prepare)

		self._excedent = done

	def __init__(self, consume, prepare, name = "Unnamed meal plan", date = ""):
		"""Initialises a MealPlan object with the following arguments:
- consume: A list specifying what meals will be consumed.
    Must have the number of days covered by the plan as length.
    Each item must be a dictionary where
        - keys are recipes to be consumed,
        - and values are the number of servings to be consumed.
- prepare: A list of the same length as consume.
    Each item must be a dictionary where
        - keys are the extra recipes that will be prepared,
        - and values are the extra servings that will be prepared.
- name: Optional name of the meal plan.
- date: Optional date of creation of the meal plan.
"""

		self.name = name
		self.date = date
		self.consume = consume
		self.set_prepare(prepare)
		self.path = ""

	def get_calories(self):
		calories = []
		for day in self.consume:
			total = 0
			for meal in day:
				total += find_component(meal).get_calories() * day[meal]
			calories.append(total)
		return calories 

	def get_ingredients(self):
		ingredients = {}
		for day in self.consume:
			for meal in day:
				_add_ingredients(ingredients, find_component(meal), day[meal])
		return ingredients

	def get_excedent(self):
		return self._excedent

	def __str__(self):
		string = self.name
		if self.date != "":
			string += f" ({self.date})"
		string += "\n\n"
		for i, day in enumerate(self.consume):
			string += f"Day {i + 1}\nCONSUME:\n"
			for item in day:
				meal = find_component(item)
				string += f"- {meal.name} (servings: {day[item]}, {math.ceil(meal.get_calories() * day[item])} kcal)\n"
			string += "PREPARE:\n"
			for recipe in self._prepare[i]:
				string += f"- {recipe.name} (servings: {self._prepare[i][recipe]})\n"
			string += "\n"
		string += f"Average daily energy: {math.ceil(statistics.mean(self.get_calories()))} kcal\n"
		if len(self._excedent) != 0:
			string += "\nEXCEDENT:\n"
			for element in self._excedent:
				string += f"{self._excedent[element]} {element.name}\n"
		return string

	def __repr__(self):
		return self.name

	def shopping_list(self):
		string = "";
		ingredients = self.get_ingredients()
		for ing in ingredients:
			string += f"{ing.name}: {ingredients[ing]} {ing.unit}\n"
		return string

	def save(self, path = ""):
		if path == "":
			path = self.path
		struct = {}
		struct["name"] = self.name
		struct["date"] = self.date
		struct["consume"] = self.consume
		struct["prepare"] = self._extra_prepare

		if not os.path.exists("mealplans"):
			os.mkdir("mealplans")

		js = json.dumps(struct)
		with open("mealplans/" + path + ".json", "w") as f:
			f.write(js)

		mealplans[path] = self

def parse_mealplan(js):
	"""Creates a MealPlan object from a JSON representation.
"""
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
	"""Loads all the meal plans in the mealplans/ folder.
They are stored in the "mealplans" dictionary.
"""
	global mealplans
	if not os.path.isdir("mealplans"):
		return
	for file in os.listdir("mealplans"):
		if not file.endswith(".json"):
			continue
		with open(f"mealplans/{file}", "r") as rfile:
			data = rfile.read()
			mealplan = parse_mealplan(data) 
			mealplan.path = file[:-5] # Remove extension (.json)
			mealplans[mealplan.path] = mealplan

load_mealplans()
