# Foodgram

Foodgram — это веб-приложение, где пользователи могут публиковать рецепты, добавлять понравившиеся рецепты в избранное и формировать список покупок. Проект включает в себя фронтенд, бэкенд и базу данных.

---

## Запуск проекта

### 1. Клонирование репозитория
```bash
git clone https://github.com/gentIeman/foodgram-st.git
cd foodgram
```

### 2. Переход в папку `infra`
```bash
cd infra
```

### 3. Создание файла `.env`
Создайте файл `.env` и заполните его следующими переменными окружения:
```env
POSTGRES_DB=foodgram
POSTGRES_USER=foodgram_user
POSTGRES_PASSWORD=foodgram_password
DB_NAME=foodgram
DB_HOST=db
DB_PORT=5432
```

### 4. Запуск Docker Compose
```bash
docker-compose up -d
```

### 5. Выполнение миграций, сборка статики и создание суперпользователя
```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py collectstatic --noinput
docker-compose exec backend python manage.py createsuperuser
```

### 6. Заполнение базы ингредиентами
Ингредиенты загружаются из файла `data/ingredients.json` с помощью команды:
```bash
docker-compose exec backend python manage.py import_ingredients
```

### 7. Доступ к приложению
- **Фронтенд**: [http://localhost](http://localhost)
- **Документация API**: [http://localhost/api/docs/](http://localhost/api/docs/)

---

## О проекте

Foodgram позволяет:
- Публиковать рецепты с описанием и изображениями.
- Добавлять рецепты в избранное.
- Формировать список покупок для выбранных рецептов.

---

## Используемые технологии

### Backend
- **Python**
- **Django и Django REST Framework (DRF)**
- **PostgreSQL**
- **Docker**
- **Nginx**

### Frontend
- **React :(**

### CI/CD
- **Docker Compose**
- **GitHub Actions**

