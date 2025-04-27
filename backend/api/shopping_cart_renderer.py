from django.utils.timezone import now
from typing import Any, List, Dict

def render_shopping_cart(user: Any, ingredients: List[Dict[str, Any]], recipes: List[Any]) -> str:
    """Генерация текста для списка покупок пользователя."""
    header = f"Список покупок на {now().strftime('%d-%m-%Y %H:%M:%S')}\n"
    ingredient_lines = [
        f"{idx}. {item['ingredient__name'].capitalize()} ({item['ingredient__measurement_unit']}) - {item['total_amount']}"
        for idx, item in enumerate(ingredients, start=1)
    ]
    recipe_lines = [f"- {recipe.name} (@{recipe.author.username})" for recipe in recipes]
    return "\n".join(
        [header, "Продукты:\n", *ingredient_lines, "\nРецепты, использующие эти продукты:\n", *recipe_lines]
    )
