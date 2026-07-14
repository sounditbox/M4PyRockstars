from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.dependencies import get_settings
from app.models import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    return get_settings().database_url


def get_alembic_section(database_url: str) -> dict[str, str]:
    section = config.get_section(
        config.config_ini_section, {}
    )
    section["sqlalchemy.url"] = database_url
    return section


def is_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def run_migrations_offline() -> None:
    database_url = get_database_url()
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=is_sqlite(database_url),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    database_url = get_database_url()
    connectable = engine_from_config(
        get_alembic_section(database_url),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                render_as_batch=is_sqlite(database_url),
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
