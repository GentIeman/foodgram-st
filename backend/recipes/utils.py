from django.db.models import Sum
from io import BytesIO


def generate_shopping_list(ingredients):
    """Генерация списка покупок"""
    shopping_list = BytesIO()

    ingredients_data = ingredients.values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(
        total_amount=Sum('amount')
    ).order_by('ingredient__name')

    content = ['Список покупок:\n\n']
    for item in ingredients_data:
        content.append(
            f'- {item["ingredient__name"]} '
            f'({item["ingredient__measurement_unit"]}) - '
            f'{item["total_amount"]}\n'
        )

    shopping_list.write(''.join(content).encode('utf-8'))
    shopping_list.seek(0)
    return shopping_list
