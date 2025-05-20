from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from .models import Subscription
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from drf_extra_fields.fields import Base64ImageField


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'id', 'username', 'first_name',
            'last_name', 'email', 'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(
            user=user,
            author=obj
        ).exists()

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return request.build_absolute_uri(obj.avatar.url)
        return ""


class UserCreateSerializer(DjoserUserCreateSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    username = serializers.CharField(
        required=True,
        max_length=150,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=(
                    'Username может содержать только буквы, '
                    'цифры и @/./+/-/_'
                )
            )
        ]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = get_user_model()
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'password'
        )

    def validate_username(self, value):
        if get_user_model().objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким username уже существует.'
            )
        return value

    def validate_email(self, value):
        if get_user_model().objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.'
            )
        return value

    def create(self, validated_data):
        user = get_user_model().objects.create_user(**validated_data)
        return user


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'recipes',
            'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        from recipes.serializers import RecipeShortSerializer
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        recipes = obj.recipes.all()

        if recipes_limit is not None:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                pass

        return RecipeShortSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = get_user_model()
        fields = ('avatar',)

    def update(self, instance, validated_data):
        instance.avatar = validated_data.get('avatar', instance.avatar)
        instance.save()
        return instance

