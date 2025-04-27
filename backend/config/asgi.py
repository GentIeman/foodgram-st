import os
from django.core.asgi import get_asgi_application

# Устанавливаем переменную окружения для использования настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Получаем ASGI-приложение Django
application = get_asgi_application()
