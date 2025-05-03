import csv
import os

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load ingredients from CSV file'

    def handle(self, *args, **options):
        file_path = os.path.join('data', 'ingredients.csv')

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    name, measurement_unit = row
                    Ingredient.objects.get_or_create(
                        name=name,
                        measurement_unit=measurement_unit
                    )
            self.stdout.write(
                self.style.SUCCESS('Ingredients loaded successfully')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error loading ingredients: {e}')
            )
