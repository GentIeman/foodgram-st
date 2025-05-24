from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from djoser.views import UserViewSet as DjoserUserViewSet
from djoser.serializers import UserCreateSerializer
import base64
from django.core.files.base import ContentFile

from .models import Subscription, User
from .serializers import (
    SubscriptionSerializer, AvatarSerializer,
    SubscribeSerializer
)


class CustomPagination(PageNumberPagination):
    page_size_query_param = 'limit'


class UserViewSet(DjoserUserViewSet):
    """Представление для пользователей"""
    pagination_class = CustomPagination

    def get_permissions(self):
        """Выбор разрешений в зависимости от действия"""
        if self.action in [
            'me', 'subscribe', 'subscriptions',
            'set_avatar', 'delete_avatar'
        ]:
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer, *args, **kwargs):
        super().perform_create(serializer)

    @action(
        detail=False,
        methods=['put', 'post'],
        url_path='me/avatar',
        url_name='me_avatar',
        permission_classes=[IsAuthenticated]
    )
    def set_avatar(self, request):
        """Установка аватара пользователя"""
        user = request.user
        serializer = AvatarSerializer(user, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        """Подписка/отписка на пользователя"""
        author = get_object_or_404(User, pk=pk)
        user = request.user

        if request.method == 'POST':
            serializer = SubscribeSerializer(data={
                'user': user.id,
                'author': author.id
            })
            serializer.is_valid(raise_exception=True)
            serializer.save()

            subscription_serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(subscription_serializer.data, status=status.HTTP_201_CREATED)

        serializer = SubscriptionSerializer(data={
            'user': user.id,
            'author': author.id
        })
        serializer.is_valid(raise_exception=True)

        subscription = Subscription.objects.get(user=user, author=author)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        """Получение списка подписок"""
        queryset = User.objects.filter(following__user=request.user)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionSerializer(
            queryset,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)
