from django.contrib import admin
from django.utils.html import mark_safe
from import_export.admin import ImportExportModelAdmin
from import_export.resources import ModelResource
from .models import (
    Ingredient, Recipe, RecipeIngredient,
    Favorite, ShoppingCart, Subscription
)
from .filters import CookingTimeFilter
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'username', 'full_name', 'email', 'avatar_preview',
        'recipe_count', 'subscription_count', 'subscriber_count'
    )
    search_fields = ('username', 'email')
    list_filter = ('is_staff', 'is_active')

    def full_name(self, obj):
        return obj.full_name()
    full_name.short_description = "ФИО"

    def avatar_preview(self, obj):
        if obj.avatar:
            return mark_safe(
                f'<img src="{obj.avatar.url}" width="50" height="50" style="border-radius:50%;">'
            )
    avatar_preview.short_description = "Аватар"
    avatar_preview.admin_order_field = "avatar"

    def recipe_count(self, obj):
        return obj.recipes.count()
    recipe_count.short_description = "Рецептов"

    def subscription_count(self, obj):
        return obj.subscribers.count()
    subscription_count.short_description = "Подписок"

    def subscriber_count(self, obj):
        return obj.authors.count()
    subscriber_count.short_description = "Подписчиков"

class IngredientResource(ModelResource):
    class Meta:
        model = Ingredient
        exclude = ('id',)
        skip_first_row = True
        encoding = 'utf-8-sig'
        import_mode = 1
        import_id_fields = []

@admin.register(Ingredient)
class IngredientAdmin(ImportExportModelAdmin):
    resource_class = IngredientResource
    list_display = ('name', 'measurement_unit')
    search_fields = ('name', 'measurement_unit')
    list_filter = ('measurement_unit',)

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ['ingredient']

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'cooking_time', 'author',
        'favorites_count', 'ingredients_list', 'image_preview'
    )
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('author', CookingTimeFilter)
    inlines = [RecipeIngredientInline]

    def favorites_count(self, obj):
        return Favorite.objects.filter(recipe=obj).count()
    favorites_count.short_description = 'В избранном'

    def ingredients_list(self, obj):
        ingredients = [
            f'{ri.ingredient.name} — {ri.amount} {ri.ingredient.measurement_unit}'
            for ri in obj.recipe_ingredients.all()
        ]
        return mark_safe("<br>".join(ingredients))
    ingredients_list.short_description = 'Ингредиенты'

    def image_preview(self, obj):
        return mark_safe(
            f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 100px; border-radius: 10px;" />'
        )
    image_preview.short_description = "Изображение"
    image_preview.admin_order_field = 'image'

@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'ingredient', 'amount')
    list_filter = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')

@admin.register(Favorite, ShoppingCart)
class UserRecipeRelationAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    list_filter = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__username', 'author__username')
