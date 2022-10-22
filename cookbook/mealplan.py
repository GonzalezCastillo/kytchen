import statistics
import math

from cookbook.recipe import *

class MealPlan:
	days = []
	
	def __init__(self, where):
		where = "mealplans/" + where
		with open(where, "r") as f:
			reader = csv.reader(f, delimiter = ";")
			for line in reader:
				day_meals = []
				for meal in line:
					day_meals.append(Recipe(meal))
				self.days.append(day_meals)
	
	def get_calories(self):
		calories = []
		for day in self.days:
			total = 0
			for meal in day:
				total += meal.get_calories()
			calories.append(total)
		return statistics.mean(calories)

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
