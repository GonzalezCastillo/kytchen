import statistics
import math

from cookbook.recipe import *

class MealPlan:

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

		if "yields" in data:
			self.scalable = True
			self.yields = data["yields"]
		else:
			self.scalable = False
			self.yields = ""

		for step in data["method"]:
			self.steps.append(Step(step[0], step[1], step[2]))

	def get_calories(self):
		calories = []
		for day in self.days:
			total = 0
			for meal in day:
				total += meal.get_calories()
			calories.append(total)
		return calories 

	def __str__(self):
		string = ""
		i = 0
		for day in self.days:
			i += 1
			string += f"Day {i}\n"
			for meal in day:
				string += f"{meal.name} ({math.ceil(meal.get_calories())} kcal)\n"
			string += "\n"
		string += f"Average daily energy: {math.ceil(self.get_calories())} kcal\n"
		return string

