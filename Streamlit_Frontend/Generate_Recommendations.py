import requests
import json

class Generator:
    def __init__(self, nutrition_input: list, ingredients: list = [], params: dict = {'n_neighbors': 5, 'return_distance': False}, cuisine: str | None = None):
        self.nutrition_input = nutrition_input
        self.ingredients = ingredients
        self.params = params
        self.cuisine = cuisine

    def set_request(self, nutrition_input: list, ingredients: list, params: dict, cuisine: str | None = None):
        self.nutrition_input = nutrition_input
        self.ingredients = ingredients
        self.params = params
        self.cuisine = cuisine

    def generate(self,):
        request = {
            'nutrition_input': self.nutrition_input,
            'ingredients': self.ingredients,
            'params': self.params,
            'cuisine': self.cuisine
        }
        response = requests.post(url='http://backend:8080/predict/', data=json.dumps(request))
        return response
