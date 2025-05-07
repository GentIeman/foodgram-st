# Foodgram

## Запуск проекта

### 1. Клонирование репозитория
```bash
git clone https://github.com/gentIeman/foodgram-st.git
cd foodgram-st
```

### 2. Переход в папку `infra`
```bash
cd infra
```

### 3. Создание файла `.env`
Создайте файл `.env` с помощью команды:
```bash
touch .env
```
или откройте его для редактирования:
```bash
nano .env
```
и заполните его следующими переменными окружения:
```env
# Django ключи
DEBUG=True
DJANGO_SECRET_KEY=mjb*_8v*o#8ekfyraixg30m%i4^)^5ledikfct@9=n=
DJANGO_ALLOWED_HOSTS=localhost
SITE_URL=http://localhost

# PostgreSQL ключи
POSTGRES_DB=foodgram
POSTGRES_USER=user
POSTGRES_PASSWORD=1234567890
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### 4. Запуск Docker Compose
```bash
docker-compose up -d
```

### 5. Выполнение миграций
```bash
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
```

### 6. Сборка статических файлов
```bash
docker-compose exec backend python manage.py collectstatic --noinput
```

### 7. Создание суперпользователя
```bash
docker-compose exec backend python manage.py createsuperuser
```

### 8. Заполнение базы ингредиентами
Ингредиенты загружаются из файла `data/ingredients.csv` с помощью команды:
```bash
docker-compose exec backend python manage.py load_ingredients
```
### 9. Перезапуск Docker compose
```bash
docker-compose up -d --build
```

### 9. Доступ к приложению
- **Фронтенд**: [http://localhost](http://localhost)
- **Документация API**: [http://localhost/api/docs/](http://localhost/api/docs/)

---

## Используемые технологии

### Backend
- **Python**
- **Django и Django REST Framework (DRF)**
- **PostgreSQL**
- **Docker**
- **Nginx**

### Frontend
- **React** 😐

### CI/CD
- **Docker Compose**
- **GitHub Actions**

---

## Остальное

- **Ссылка на Docker Hub Profile**: [Docker Hub](https://hub.docker.com/u/gentieman)
- **Выполнил**: Шепелев Илья Алексеевич, Группа 15.27Д-ПИ04у/23б
