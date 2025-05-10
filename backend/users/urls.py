from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet, basename='users')

urlpatterns = [
    path('users/me/avatar/', views.UserViewSet.as_view({
        'put': 'set_avatar',
        'post': 'set_avatar',
        'delete': 'delete_avatar'
    })),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
