from logging.config import fileConfig
from pathlib import Path
import os

from alembic import context
from sqlalchemy import engine_from_config, pool, event

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        database_url = env_url
    else:
        database_url = config.get_main_option("sqlalchemy.url")
    if database_url and database_url.startswith("sqlite:///"):
        relative_path = database_url[len("sqlite:///"):]
        absolute_path = Path(relative_path).resolve()
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{absolute_path}"
    return database_url or "sqlite:///data/nexsusguard.db"


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    @event.listens_for(connectable, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=None,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
