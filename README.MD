# Products API

Учебный проект на FastAPI: каталог товаров, категории, JWT-аутентификация и
гибкие характеристики товаров.

## Стек

- FastAPI и Pydantic;
- SQLAlchemy и Alembic;
- PostgreSQL для пользователей, категорий и товаров;
- MongoDB для характеристик товаров;
- PyMongo с асинхронным клиентом;
- pytest.

PostgreSQL хранит основные сущности и связи между ними. MongoDB хранит документы
`product_attributes`, структура которых может различаться для разных товаров.
Поле `product_id` связывает документ с товаром в PostgreSQL и имеет уникальный
индекс.

## Запуск

Требуются Python 3.14+, [uv](https://docs.astral.sh/uv/) и Docker.

Установите зависимости:

```bash
uv sync
```

Создайте `.env` в корне проекта:

```dotenv
APP_NAME="Products API Local"
DEBUG=true
API_PREFIX=/api/v1

JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/products
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin

MONGODB_URL=mongodb://mongo:mongo@localhost:27017/?authSource=admin
MONGODB_DATABASE=products
```

Поднимите базы данных и дождитесь их готовности:

```bash
docker compose up -d --wait postgres mongo
```

Примените миграции PostgreSQL:

```bash
uv run alembic upgrade head
```

Запустите API:

```bash
uv run uvicorn app.main:app --reload
```

Swagger UI будет доступен по адресу
[http://localhost:8000/docs](http://localhost:8000/docs).

## API

Все маршруты приложения используют префикс `/api/v1`.

| Метод и маршрут | Назначение | Доступ |
| --- | --- | --- |
| `GET /health` | Проверка состояния API | Публичный |
| `POST /auth/token` | Получение JWT | Публичный |
| `GET /auth/me` | Текущий пользователь | Авторизованный |
| `GET /categories` | Список категорий | Публичный |
| `POST /categories` | Создание категории | Администратор |
| `GET /products` | Список и фильтрация товаров | Публичный |
| `GET /products/{id}` | Карточка товара | Публичный |
| `POST /products` | Создание товара | Администратор |
| `PUT/PATCH/DELETE /products/{id}` | Изменение товара | Администратор |
| `GET /products/{id}/attributes` | Характеристики из MongoDB | Публичный |
| `PUT/PATCH/DELETE /products/{id}/attributes` | Изменение характеристик | Администратор |

Пример документа с характеристиками:

```json
{
  "attributes": {
    "color": "black",
    "wireless": true,
    "weight_grams": 95
  }
}
```

`PUT` создаёт документ или полностью заменяет `attributes`, `PATCH` обновляет
только переданные ключи. Имена характеристик не могут начинаться с `$` или
содержать `.`, поскольку эти символы имеют специальное значение в MongoDB.

## Проверка

```bash
uv run pytest
```

Тесты используют временную SQLite-базу и не требуют запущенных PostgreSQL или
MongoDB. Для ручной проверки MongoDB запустите сервисы через Compose и работайте
с attributes-маршрутами через Swagger UI.

## Структура

```text
app/
  core/config.py                 настройки из окружения
  database.py                    SQLAlchemy engine и session factory
  lifespan.py                    PostgreSQL, bootstrap admin и MongoDB
  mongodb.py                     индексы коллекции MongoDB
  models.py                      SQLAlchemy-модели
  routers/
    products.py                  CRUD товаров
    categories.py                категории
    auth.py                      JWT-аутентификация
    product_attributes.py        CRUD характеристик в MongoDB
alembic/                         миграции PostgreSQL
tests/                           тесты API
docker-compose.yml               PostgreSQL и MongoDB
```
