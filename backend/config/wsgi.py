import os
from django.core.wsgi import get_wsgi_application

# Устанавливаем переменную окружения для использования настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# Получаем WSGI-приложение Django
application = get_wsgi_application()
