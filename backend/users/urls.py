from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views
from djoser.views import UserViewSet as DjoserUserViewSet

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='users')

urlpatterns = [
    path('users/me/avatar/', views.UserViewSet.as_view({
        'put': 'set_avatar',
        'post': 'set_avatar',
        'delete': 'delete_avatar'
    })),
    path('users/set_password/', DjoserUserViewSet.as_view({'post': 'set_password'})),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
