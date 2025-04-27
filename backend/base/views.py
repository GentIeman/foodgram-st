from django.shortcuts import redirect, get_object_or_404
from django.http import Http404
from .models import Recipe

def short_link(request, pk):
    """Генерирует короткую ссылку для рецепта и перенаправляет на его абсолютный URL."""
    try:
        recipe = Recipe.objects.get(pk=pk)
    except Recipe.DoesNotExist:
        raise Http404("Рецепт не найден")
    return redirect(recipe.get_absolute_url())
