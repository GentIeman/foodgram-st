from typing import Any
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Sum
from django.db.models.query import QuerySet
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.request import Request
from base.models import Ingredient, Recipe, Favorite, Subscription, ShoppingCart, RecipeIngredient
from .serializers import (
    IngredientSerializer,
    RecipeSerializer,
    UserSerializer,
    AvatarSerializer,
    UserSubscriptionSerializer,
)
from .shopping_cart_renderer import render_shopping_cart
from .permissions import IsAuthorOrReadOnly

User = get_user_model()

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с ингредиентами."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self) -> QuerySet:
        """Фильтрация ингредиентов по имени."""
        queryset = Ingredient.objects.all().order_by("name")
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с рецептами."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_queryset(self) -> QuerySet:
        """Фильтрация рецептов по автору, корзине и избранному."""
        queryset = Recipe.objects.all().order_by("-date_published")
        params = self.request.query_params

        author_id = params.get("author")
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        if self.request.user.is_authenticated:
            is_in_shopping_cart = params.get("is_in_shopping_cart")
            if is_in_shopping_cart is not None:
                if is_in_shopping_cart == "1":
                    queryset = queryset.filter(shoppingcart__user=self.request.user)
                elif is_in_shopping_cart == "0":
                    queryset = queryset.exclude(shoppingcart__user=self.request.user)

            is_favorited = params.get("is_favorited")
            if is_favorited is not None:
                if is_favorited == "1":
                    queryset = queryset.filter(favorite__user=self.request.user)
                elif is_favorited == "0":
                    queryset = queryset.exclude(favorite__user=self.request.user)

        return queryset.distinct()

    def perform_create(self, serializer: Any) -> None:
        """Создание рецепта с указанием автора."""
        serializer.save(author=self.request.user)

    @staticmethod
    def handle_favorite_or_cart(request: Request, model: Any, pk: Any) -> Response:
        """Обрабатывает добавление и удаление рецепта в корзину или избранное."""
        recipe = get_object_or_404(Recipe, id=pk)
        user = request.user

        if request.method == "POST":
            _, created = model.objects.get_or_create(user=user, recipe=recipe)
            if created:
                return Response({"status": "Рецепт добавлен"}, status=status.HTTP_201_CREATED)
            return Response({"status": "Рецепт уже в списке"}, status=status.HTTP_400_BAD_REQUEST)

        get_object_or_404(model, user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post", "delete"])
    def shopping_cart(self, request: Request, pk: Any = None) -> Response:
        """Добавление и удаление рецептов из корзины покупок."""
        return self.handle_favorite_or_cart(request, ShoppingCart, pk)

    @action(detail=True, methods=["post", "delete"])
    def favorite(self, request: Request, pk: Any = None) -> Response:
        """Добавление и удаление рецептов из избранного."""
        return self.handle_favorite_or_cart(request, Favorite, pk)

    @action(detail=False, methods=["get"])
    def download_shopping_cart(self, request: Request) -> FileResponse:
        """Скачивание списка покупок."""
        user = request.user
        ingredients = (
            RecipeIngredient.objects.filter(recipe__shoppingcart__user=user)
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total_amount=Sum("amount"))
            .order_by("ingredient__name")
        )
        recipes = Recipe.objects.filter(shoppingcart__user=user)
        shopping_cart_text = render_shopping_cart(user, ingredients, recipes)
        return FileResponse(
            shopping_cart_text,
            as_attachment=True,
            filename="shopping_cart.txt",
            content_type="text/plain",
        )

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request: Request, pk: Any = None) -> Response:
        """Генерация короткой ссылки на рецепт."""
        recipe = self.get_object()
        short_url = request.build_absolute_uri(reverse("short_link", args=[recipe.pk]))
        return Response({"short-link": short_url}, status=status.HTTP_200_OK)


class UserViewSet(DjoserUserViewSet):
    """ViewSet для управления пользователями."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"  # Используем ID для поиска пользователей

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request: Request) -> Response:
        """Управление аватаром пользователя."""
        user = request.user
        if request.method == "DELETE":
            if user.avatar:
                user.avatar.delete()
                user.avatar = None
                user.save()
                return Response({"avatar": None}, status=status.HTTP_204_NO_CONTENT)
            raise ValidationError({"error": "Аватар отсутствует"})
        serializer = AvatarSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            raise ValidationError(serializer.errors)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request: Request) -> Response:
        """Получение списка подписок пользователя."""
        subscriptions = request.user.subscribers.select_related("author").prefetch_related("author__recipes")
        authors = [subscription.author for subscription in subscriptions]
        page = self.paginate_queryset(authors)
        serializer = UserSubscriptionSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post", "delete"], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request: Request, id: Any = None) -> Response:
        """Подписка и отписка от автора."""
        user = request.user
        author = get_object_or_404(User, id=id)
        if user == author:
            raise ValidationError({"errors": "Действие невозможно для самого себя"})
        if request.method == "POST":
            subscription, created = Subscription.objects.get_or_create(user=user, author=author)
            if not created:
                raise ValidationError({"errors": "Вы уже подписаны"})
            return Response({"status": "Подписка успешно добавлена"}, status=status.HTTP_201_CREATED)
        get_object_or_404(Subscription, user=user, author=author).delete()
        return Response({"status": "Вы успешно отписались"}, status=status.HTTP_204_NO_CONTENT)
