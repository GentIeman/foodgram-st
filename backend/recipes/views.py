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
from rest_framework.filters import SearchFilter
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.db.models import Exists, OuterRef
from rest_framework import serializers
from django.http import Http404

from .models import (
    Ingredient,
    Recipe,
    Favorite,
    ShoppingCart,
    RecipeIngredient
)
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    RecipeCreateSerializer,
    RecipeShortSerializer
)
from .filters import RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .utils import generate_shopping_list


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Представление для ингредиентов"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = (SearchFilter,)
    search_fields = ('^name',)


class RecipeViewSet(viewsets.ModelViewSet):
    """Представление для рецептов"""
    queryset = Recipe.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [IsAuthorOrReadOnly]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action in ['create', 'partial_update', 'update']:
            return RecipeCreateSerializer
        return RecipeSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all()
        user = self.request.user

        try:
            if user.is_authenticated:
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

                # Фильтрация по is_favorited
                is_favorited = self.request.query_params.get('is_favorited')
                if is_favorited is not None:
                    try:
                        is_favorited = is_favorited.lower() in ('true', '1', 't', 'y', 'yes')
                        if is_favorited:
                            queryset = queryset.filter(favorited_by__user=user)
                    except (AttributeError, ValueError):
                        pass

                # Фильтрация по is_in_shopping_cart
                is_in_shopping_cart = self.request.query_params.get('is_in_shopping_cart')
                if is_in_shopping_cart is not None:
                    try:
                        is_in_shopping_cart = is_in_shopping_cart.lower() in ('true', '1', 't', 'y', 'yes')
                        if is_in_shopping_cart:
                            queryset = queryset.filter(in_shopping_cart__user=user)
                    except (AttributeError, ValueError):
                        pass
        except Exception:
            # Fallback to unfiltered queryset on any error
            queryset = Recipe.objects.all()

        return queryset.order_by('-pub_date')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Re-serialize with full context to include all fields
        instance = serializer.instance
        response_serializer = self.get_serializer(instance, context={'request': request})
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        
        # Ensure ingredients are present in the request data
        if 'ingredients' not in request.data:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Ensure ingredients is not empty
        if not request.data.get('ingredients'):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check all ingredients exist and have valid amounts
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
                
                # Check ingredient exists
                try:
                    ingredient_id = int(ingredient_id)
                    if not Ingredient.objects.filter(id=ingredient_id).exists():
                        return Response(
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check amount is valid
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
            
        # Check for duplicate ingredients
        ingredient_ids = [int(ingredient.get('id')) for ingredient in request.data.get('ingredients', [])]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check for required fields
        required_fields = ['name', 'text', 'cooking_time']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # Validate cooking_time
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
            
        # Ensure image is present
        if 'image' not in request.data:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )
            
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
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

    def destroy(self, request, *args, **kwargs):
        """Удаление рецепта"""
        try:
            instance = get_object_or_404(Recipe, id=kwargs.get('pk'))
            
            # Check if user has permission
            if instance.author != request.user:
                return Response(status=status.HTTP_403_FORBIDDEN)
                
            # Delete the recipe
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта из избранного"""
        try:
            recipe = get_object_or_404(Recipe, id=pk)
            
            if request.method == 'POST':
                if Favorite.objects.filter(user=request.user, recipe=recipe).exists():
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )
                Favorite.objects.create(user=request.user, recipe=recipe)
                serializer = RecipeShortSerializer(recipe)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            # DELETE method
            favorite = get_object_or_404(
                Favorite, 
                user=request.user, 
                recipe=recipe
            )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Http404:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        try:
            recipe = get_object_or_404(Recipe, id=pk)
            
            if request.method == 'POST':
                if ShoppingCart.objects.filter(user=request.user, recipe=recipe).exists():
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST
                    )
                ShoppingCart.objects.create(user=request.user, recipe=recipe)
                serializer = RecipeShortSerializer(recipe)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            shopping_cart = get_object_or_404(
                ShoppingCart, 
                user=request.user, 
                recipe=recipe
            )
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = ShoppingCart.objects.filter(user=user)
        
        ingredients = {}
        for item in shopping_cart:
            recipe = item.recipe
            for recipe_ingredient in recipe.recipe_ingredients.all():
                ingredient = recipe_ingredient.ingredient
                amount = recipe_ingredient.amount
                key = (ingredient.name, ingredient.measurement_unit)
                ingredients[key] = ingredients.get(key, 0) + amount

        shopping_list = ['Список покупок:\n']
        for (name, unit), amount in ingredients.items():
            shopping_list.append(f'{name} - {amount} {unit}\n')

        response = HttpResponse(
            ''.join(shopping_list),
            content_type='text/plain'
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
        site_url = settings.SITE_URL
        return Response(
            {"short-link": f"{site_url}/recipes/{recipe.id}"},
            status=status.HTTP_200_OK
        )
