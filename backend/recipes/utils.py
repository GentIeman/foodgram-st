from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
import os

def generate_shopping_list(
    user,
    ingredients,
    recipes
) -> HttpResponse:
    """Генерация списка покупок"""
    content = f"Список покупок для {user.username}:\n\n"
    
    for ingredient in ingredients:
        content += f"- {ingredient['ingredient__name']}: {ingredient['amount']} {ingredient['ingredient__measurement_unit']}\n"
    
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
    
    return response 