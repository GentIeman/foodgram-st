from typing import Any, Dict, List
from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer as DjoserUserSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.password_validation import validate_password
from base.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Subscription,
    Favorite,
    ShoppingCart,
)

User = get_user_model()

class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара пользователя."""
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ("avatar",)


class UserSerializer(DjoserUserSerializer):
    """Сериализатор для пользователя с указанием статуса подписки."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )

    def get_request(self) -> Any:
        return self.context.get("request")

    def get_is_subscribed(self, author: Any) -> bool:
        request = self.get_request()
        return bool(
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(user=request.user, author=author).exists()
        )


class UserSubscriptionSerializer(UserSerializer):
    """Сериализатор для пользователя с подписками и рецептами."""
    recipes_count = serializers.IntegerField(source="recipes.count", read_only=True)
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )

    def get_recipes(self, author: Any) -> List[Dict[str, Any]]:
        request = self.context.get("request")
        recipes_limit = int(request.GET.get("recipes_limit", 10**10)) if request else 10**10
        from .serializers import RecipeSerializer  # для избежания циклических импортов
        return RecipeSerializer(
            author.recipes.all()[:recipes_limit], many=True, context=self.context
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(), source="ingredient")
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(source="ingredient.measurement_unit", read_only=True)
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов."""
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(source="recipe_ingredients", many=True)
    cooking_time = serializers.IntegerField(min_value=1, required=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )

    def get_request(self) -> Any:
        return self.context.get("request")

    def _check_flag(self, obj: Any, model: Any) -> bool:
        request = self.get_request()
        return bool(
            request
            and request.user.is_authenticated
            and model.objects.filter(user=request.user, recipe=obj).exists()
        )

    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ingredients = data.get("recipe_ingredients", [])
        if not ingredients:
            raise serializers.ValidationError("Должен быть хотя бы один ингредиент.")
        # другим способом решить этот костыль у меня не получилось ;)
        ingredient_ids = {ingredient["ingredient"].id for ingredient in ingredients}
        if len(ingredient_ids) != len(ingredients):
            raise serializers.ValidationError("Дублирование ингредиентов не допускается.")
        return data

    def get_is_favorited(self, obj: Any) -> bool:
        return self._check_flag(obj, Favorite)

    def get_is_in_shopping_cart(self, obj: Any) -> bool:
        return self._check_flag(obj, ShoppingCart)

    def create(self, validated_data: Dict[str, Any]) -> Recipe:
        ingredients_data = validated_data.pop("recipe_ingredients", [])
        recipe = Recipe.objects.create(**validated_data)
        self._create_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance: Recipe, validated_data: Dict[str, Any]) -> Recipe:
        ingredients_data = validated_data.pop("recipe_ingredients", [])
        instance.recipe_ingredients.all().delete()
        self._create_recipe_ingredients(instance, ingredients_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def _create_recipe_ingredients(self, recipe: Recipe, ingredients_data: List[Dict[str, Any]]) -> None:
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=ingredient_data["ingredient"],
                    amount=ingredient_data["amount"],
                )
                for ingredient_data in ingredients_data
            ]
        )