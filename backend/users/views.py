from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
import base64
from django.core.files.base import ContentFile

from .models import Subscription
from .serializers import (
    UserSerializer, UserCreateSerializer,
    SubscriptionSerializer
)

User = get_user_model()


class CustomPagination(PageNumberPagination):
    page_size_query_param = 'limit'


class UserViewSet(viewsets.ModelViewSet):
    """Представление для пользователей"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination
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
        if self.action in ['me', 'set_password', 'subscribe', 'subscriptions', 'set_avatar', 'delete_avatar']:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Получение и обновление данных текущего пользователя"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'post'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def set_avatar(self, request):
        """Установка аватара пользователя"""
        user = request.user
        avatar_data = request.data.get('avatar')

        if not avatar_data:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            format, imgstr = avatar_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'avatar_{user.id}.{ext}'
            )
            user.avatar = data
            user.save()
            serializer = self.get_serializer(user, context={'request': request})
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )
        except (ValueError, TypeError, base64.binascii.Error):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated]
    )
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            if user.avatar.storage.exists(user.avatar.name):
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
            if user == author:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Subscription.objects.filter(
                user=user,
                author=author
            ).exists():
                return Response(
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

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """Изменение пароля пользователя"""
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(current_password):
            return Response(
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
