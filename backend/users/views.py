from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import base64
from django.core.files.base import ContentFile

from .models import Subscription
from .serializers import (
    UserSerializer, UserCreateSerializer,
    SubscriptionSerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Представление для пользователей"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['subscriptions', 'subscribe']:
            return SubscriptionSerializer
        return UserSerializer

    def get_permissions(self):
        """Выбор разрешений в зависимости от действия"""
        if self.action in ['subscribe', 'subscriptions', 'set_password']:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(
        detail=False,
        methods=['get', 'put', 'patch'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Получение и обновление данных текущего пользователя"""
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

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
            if user == author:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(
                user=user,
                author=author
            ).exists():
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=user, author=author)
            serializer = SubscriptionSerializer(
                author,
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = get_object_or_404(
            Subscription,
            user=user,
            author=author
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
        url_name='subscriptions'
    )
    def subscriptions(self, request):
        """Получение списка подписок"""
        user = request.user
        queryset = User.objects.filter(following__user=user)
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

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def update_avatar(self, request):
        """Обновление аватара пользователя"""
        user = request.user
        avatar_data = request.data.get('avatar')

        if not avatar_data:
            return Response(
                {'error': 'Аватар не предоставлен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            format, imgstr = avatar_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'image.{ext}'
            )
            user.avatar = data
            user.save()
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        except (ValueError, TypeError, base64.binascii.Error):
            return Response(
                {'error': 'Некорректный формат изображения'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated],
        url_path='set_password'
    )
    def set_password(self, request):
        """Изменение пароля пользователя"""
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                {'error': 'Необходимо указать текущий и новый пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                {'error': 'Неверный текущий пароль'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response(
            {'message': 'Пароль успешно изменен'},
            status=status.HTTP_200_OK
        )
