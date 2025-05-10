from django_filters import rest_framework as filters
from .models import Recipe


class RecipeFilter(filters.FilterSet):
    """Фильтр для рецептов"""
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    author = filters.NumberFilter(field_name='author__id')

    class Meta:
        model = Recipe
        fields = ['is_favorited', 'is_in_shopping_cart', 'author']

    def filter_is_favorited(self, queryset, name, value):
        """Фильтр по избранному"""
        user = self.request.user
        if value and user.is_authenticated:
            try:
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 't', 'y', 'yes')
                
                if value:
                    return queryset.filter(favorited_by__user=user)
                return queryset
            except Exception:
                return queryset
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """Фильтр по списку покупок"""
        user = self.request.user
        if value and user.is_authenticated:
            try:
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 't', 'y', 'yes')
                
                if value:
                    return queryset.filter(in_shopping_cart__user=user)
                return queryset
            except Exception:
                return queryset
        return queryset
