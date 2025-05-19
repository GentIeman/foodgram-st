from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
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
from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly


class CustomPagination(PageNumberPagination):
    """Пагинация с настраиваемым размером страницы"""
    page_size = 6
    page_size_query_param = 'limit'
    max_page_size = 100


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление для ингредиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        """Получение списка ингредиентов с фильтрацией по имени"""
        name = self.request.query_params.get('name')
        queryset = Ingredient.objects.all()
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset.order_by('name')


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
        user = self.request.user

        if not user.is_authenticated:
            return queryset.order_by('-pub_date')

        queryset = queryset.annotate(
            is_favorited=Exists(
                Favorite.objects.filter(
                    user=user,
                    recipe=OuterRef('pk')
                )
            ),
            is_in_shopping_cart=Exists(
                ShoppingCart.objects.filter(
                    user=user,
                    recipe=OuterRef('pk')
                )
            )
        )
        return queryset.order_by('-pub_date')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        instance = serializer.instance
        response_serializer = self.get_serializer(
            instance,
            context={'request': request}
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)

        if 'ingredients' not in request.data:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.data.get('ingredients'):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            for ingredient in request.data.get('ingredients', []):
                ingredient_id = ingredient.get('id')
                amount = ingredient.get('amount')

                if not ingredient_id:
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if not amount:
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    ingredient_id = int(ingredient_id)
                    if not Ingredient.objects.filter(
                        id=ingredient_id
                    ).exists():
                        return Response(
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    amount = int(amount)
                    if amount < 1:
                        return Response(
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except Exception:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        ingredient_ids = [
            int(ingredient.get('id'))
            for ingredient in request.data.get('ingredients', [])
        ]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        required_fields = ['name', 'text', 'cooking_time']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            cooking_time = int(request.data.get('cooking_time', 0))
            if cooking_time < 1:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        if 'image' not in request.data:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except serializers.ValidationError:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

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
        from .serializers import FavoriteSerializer
        return self._handle_add_remove(request, pk, Favorite, FavoriteSerializer)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        from .serializers import ShoppingCartSerializer
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
