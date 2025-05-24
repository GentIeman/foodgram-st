from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart
)
import base64
from django.core.files.base import ContentFile
from users.models import Subscription
from drf_extra_fields.fields import Base64ImageField
from users.serializers import UserSerializer

class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов"""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте"""
    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ингредиентов в рецепте"""
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов"""
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time'
        )

    def get_is_favorited(self, obj):
        """Проверяет, находится ли рецепт в избранном"""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(
            user=request.user,
            recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, находится ли рецепт в списке покупок"""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(
            user=request.user,
            recipe=obj
        ).exists()


class RecipeCreateSerializer(RecipeSerializer):
    """Сериализатор для создания рецепта"""
    ingredients = RecipeIngredientCreateSerializer(many=True, write_only=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text',
            'cooking_time'
        )
        read_only_fields = ('author', 'is_favorited', 'is_in_shopping_cart')

    def validate_ingredients(self, value):
        """Валидация ингредиентов"""
        if not value:
            raise serializers.ValidationError(
                'Нужен хотя бы один ингредиент'
            )

        ingredient_ids = []
        for item in value:
            ingredient = item['id']
            amount = item.get('amount')

            if not amount or amount < 1:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть положительным числом'
                )

            if ingredient.id in ingredient_ids:
                raise serializers.ValidationError(
                    'Ингредиенты не должны повторяться'
                )
            ingredient_ids.append(ingredient.id)

        return value

    def validate_cooking_time(self, value):
        """Валидация времени приготовления"""
        if value < 1:
            raise serializers.ValidationError(
                'Время приготовления должно быть не менее 1 минуты'
            )
        return value

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError('Изображение не может быть пустым.')
        return value

    def validate(self, data):
        # Проверка наличия поля ingredients при создании/обновлении
        if 'ingredients' not in self.initial_data:
            raise serializers.ValidationError({
                'ingredients': 'Это поле обязательно.'
            })
        return super().validate(data)

    def create_ingredients(self, recipe, ingredients):
        """Создание ингредиентов для рецепта"""
        recipe_ingredients = []
        for item in ingredients:
            recipe_ingredients.append(
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=item['id'],
                    amount=item['amount']
                )
            )
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта"""
        if 'ingredients' in validated_data:
            ingredients = validated_data.pop('ingredients')
            instance.recipe_ingredients.all().delete()
            self.create_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Преобразование объекта в словарь"""
        representation = super().to_representation(instance)
        representation['ingredients'] = RecipeIngredientSerializer(
            instance.recipe_ingredients.all(),
            many=True
        ).data
        return representation


class BaseUserRecipeRelationSerializer(serializers.ModelSerializer):
    def validate(self, data):
        user = data['user']
        recipe = data['recipe']
        model = self.Meta.model
        if self.context['request'].method == 'POST' and model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(self.Meta.already_exists_message)
        return data

class FavoriteSerializer(BaseUserRecipeRelationSerializer):
    class Meta:
        model = Favorite
        fields = ('user', 'recipe')
        already_exists_message = 'Рецепт уже в избранном.'
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=['user', 'recipe'],
                message=already_exists_message
            )
        ]

class ShoppingCartSerializer(BaseUserRecipeRelationSerializer):
    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        already_exists_message = 'Рецепт уже в списке покупок.'
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=['user', 'recipe'],
                message=already_exists_message
            )
        ]
