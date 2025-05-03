from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart
)
import base64
from django.core.files.base import ContentFile

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователей"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов"""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')

class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте"""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(source='ingredient.measurement_unit')

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

    def create(self, validated_data):
        ingredient = validated_data.pop('id')
        return RecipeIngredient.objects.create(
            ingredient=ingredient,
            **validated_data
        )

    def to_representation(self, instance):
        if isinstance(instance, Ingredient):
            return {
                'id': instance.id,
                'amount': None  # или можно убрать это поле вообще
            }
        return {
            'id': instance.ingredient.id,
            'amount': instance.amount
        }

class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для рецептов"""
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='recipeingredient_set',
        many=True,
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'image', 'text',
            'ingredients', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart'
        )

    def get_is_favorited(self, obj):
        """Проверяет, находится ли рецепт в избранном"""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favorite.objects.filter(user=request.user, recipe=obj).exists()

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, находится ли рецепт в списке покупок"""
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=request.user, recipe=obj).exists()

class RecipeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта"""
    ingredients = RecipeIngredientCreateSerializer(many=True)
    image = serializers.CharField(required=True)
    author = serializers.HiddenField(default=None, write_only=True)

    class Meta:
        model = Recipe
        fields = (
            'ingredients', 'image',
            'name', 'text', 'cooking_time',
            'author'
        )
        read_only_fields = ('author',)

    def validate_image(self, value):
        """Валидация и обработка base64 изображения"""
        if not value.startswith('data:image/'):
            raise serializers.ValidationError(
                'Некорректный формат изображения'
            )
        
        try:
            format, imgstr = value.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'image_{ext}')
            return data
        except Exception:
            raise serializers.ValidationError(
                'Некорректный формат base64 изображения'
            )

    def validate(self, data):
        """Валидация данных рецепта"""
        ingredients = data.get('ingredients')
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Добавьте хотя бы один ингредиент'}
            )
        
        ingredient_ids = [item['id'].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться'}
            )

        return data

    def create(self, validated_data):
        """Создание рецепта"""
        ingredients_data = validated_data.pop('ingredients')
        validated_data.pop('author', None)
        
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            name=validated_data['name'],
            text=validated_data['text'],
            cooking_time=validated_data['cooking_time'],
            image=validated_data['image']
        )
        
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        
        return recipe

    def update(self, instance, validated_data):
        """Обновление рецепта"""
        ingredients_data = validated_data.pop('ingredients')
        
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time', instance.cooking_time)
        instance.image = validated_data.get('image', instance.image)
        
        instance.ingredients.clear()
        
        for ingredient_data in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=instance,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
        
        instance.save()
        return instance