import csv
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из CSV файла'

    def handle(self, *args, **options):
        # Путь к файлу относительно корня проекта в контейнере
        file_path = '/app/data/ingredients.csv'

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
                self.style.SUCCESS('Ингредиенты успешно загружены')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при загрузке ингредиентов: {e}')
            )
