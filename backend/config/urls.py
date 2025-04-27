from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Определяем маршруты URL для проекта
urlpatterns = [
    path('', include('base.urls')),   # Маршруты базового приложения
    path('api/', include('api.urls')),  # Маршруты API
    path('admin/', admin.site.urls),    # Административная панель
]

if settings.DEBUG:
    # В режиме отладки подключаем маршруты для файлов media
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
