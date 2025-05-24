from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    AllowAny
)
from rest_framework.response import Response
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Exists, OuterRef
from rest_framework import serializers
from django.http import Http404
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter

from .models import (
    Ingredient,
    Recipe,
    Favorite,
    ShoppingCart
)
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    RecipeShortSerializer
)
from .filters import RecipeFilter, IngredientFilter
from .permissions import IsAuthorOrReadOnly

from .serializers import ShoppingCartSerializer
from .serializers import FavoriteSerializer


class CustomPagination(PageNumberPagination):
    """Пагинация с настраиваемым размером страницы"""
    page_size = 6
    page_size_query_param = 'limit'


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление для ингредиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter
    permission_classes = [AllowAny]
    pagination_class = None
# Без DjangoFilterBackend падает get_ingredients_list_with_name_filter // User
    filter_backends = (filters.SearchFilter, DjangoFilterBackend)
    search_fields = ['^name']


class RecipeViewSet(viewsets.ModelViewSet):
    """Представление для рецептов"""
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action in ['create', 'partial_update', 'update']:
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all()
        return queryset.order_by('-pub_date')

    def _handle_add_remove(self, request, pk, model, serializer_class):
        try:
            recipe = get_object_or_404(Recipe, id=pk)
            data = {'user': request.user.id, 'recipe': recipe.id}
            context = {'request': request}
            if request.method == 'POST':
                serializer = serializer_class(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                model.objects.create(user=request.user, recipe=recipe)
                return Response(RecipeShortSerializer(recipe).data, status=status.HTTP_201_CREATED)
            obj = model.objects.filter(user=request.user, recipe=recipe).first()
            if not obj:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        return self._handle_add_remove(request, pk, Favorite, FavoriteSerializer)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_add_remove(request, pk, ShoppingCart, ShoppingCartSerializer)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        from django.db.models import Sum, F
        try:
            ingredients = (
                Recipe.ingredients.through.objects
                .filter(recipe__shoppingcart__user=user)
                .values(name=F('ingredient__name'), unit=F('ingredient__measurement_unit'))
                .annotate(amount=Sum('amount'))
                .order_by('name')
            )
        except Exception:
            ingredients = []

        shopping_list = ['Список покупок:\n']
        for ingredient in ingredients:
            shopping_list.append(f"{ingredient['name']} - {ingredient['amount']} {ingredient['unit']}\n")

        response = HttpResponse(
            ''.join(shopping_list),
            content_type='text/plain',
            status=status.HTTP_200_OK
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def get_link(self, request, pk=None):
        """Получение ссылки на рецепт"""
        recipe = self.get_object()
        absolute_url = request.build_absolute_uri(f"/recipes/{recipe.id}")
        return Response(
            {"short-link": absolute_url},
            status=status.HTTP_200_OK
        )
