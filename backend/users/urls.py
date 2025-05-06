from django.urls import include, path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter(trailing_slash=True)
router.register('users', views.UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
