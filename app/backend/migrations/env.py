from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from compass.config import Settings
from compass.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
url = Settings().database_url
if not url:
    raise RuntimeError("Set DATABASE_URL to a dedicated PostgreSQL database before migrating.")

if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()
