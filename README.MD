# Products API

Учебный проект на FastAPI: каталог товаров, категории, JWT-аутентификация и
гибкие характеристики товаров.

## Стек

- FastAPI и Pydantic;
- SQLAlchemy и Alembic;
- PostgreSQL для пользователей, категорий и товаров;
- MongoDB для характеристик товаров;
- PyMongo с асинхронным клиентом;
- Redis для кэша, rate limiting и результатов Celery;
- RabbitMQ и aio-pika для событий каталога;
- Celery для фоновых и периодических задач;
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

REDIS_URL=redis://localhost:6379/0
PRODUCT_CACHE_TTL_SECONDS=60
AUTH_RATE_LIMIT_PER_MINUTE=5

RABBITMQ_URL=amqp://guest:guest@localhost:5672/
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

Поднимите базы данных и дождитесь их готовности:

```bash
docker compose up -d --wait postgres mongo redis rabbitmq
```

Примените миграции PostgreSQL:

```bash
uv run alembic upgrade head
```

Запустите API:

```bash
uv run uvicorn app.main:app --reload
```

В отдельных терминалах можно запустить consumer событий, Celery worker,
планировщик и Flower:

```bash
uv run python -m app.consumers.product_events
uv run celery -A app.celery_app:celery_app worker --loglevel=info --pool=solo
uv run celery -A app.celery_app:celery_app beat --loglevel=info
uv run celery -A app.celery_app:celery_app flower --port=5555
```

На Linux и macOS параметр `--pool=solo` можно убрать. RabbitMQ Management
доступен на [http://localhost:15672](http://localhost:15672), Flower — на
[http://localhost:5555](http://localhost:5555). Для локального RabbitMQ
используются `guest` / `guest`.

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
| `POST /events/products/{id}` | Публикация snapshot-события в RabbitMQ | Администратор |
| `POST /jobs/product-reports` | Запуск отчёта через Celery | Администратор |
| `GET /jobs/{task_id}` | Статус и результат Celery-задачи | Администратор |

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

Тесты используют временную SQLite-базу и тестовые реализации внешних сервисов,
поэтому не требуют запущенных PostgreSQL, MongoDB, Redis или RabbitMQ. Для
интеграционной проверки запустите Compose, consumer и Celery worker, затем
работайте с events/jobs-маршрутами через Swagger UI.

## Структура

```text
app/
  core/config.py                 настройки из окружения
  database.py                    SQLAlchemy engine и session factory
  lifespan.py                    клиенты PostgreSQL, MongoDB, Redis, RabbitMQ
  messaging.py                   RabbitMQ producer и durable-сообщения
  celery_app.py                  конфигурация Celery и Beat
  tasks.py                       фоновые задачи каталога
  mongodb.py                     индексы коллекции MongoDB
  models.py                      SQLAlchemy-модели
  routers/
    products.py                  CRUD товаров
    categories.py                категории
    auth.py                      JWT-аутентификация
    product_attributes.py        CRUD характеристик в MongoDB
    events.py                    публикация событий RabbitMQ
    jobs.py                      запуск и отслеживание Celery-задач
  consumers/
    product_events.py            RabbitMQ consumer событий каталога
alembic/                         миграции PostgreSQL
tests/                           тесты API
docker-compose.yml               PostgreSQL, MongoDB, Redis и RabbitMQ
```
