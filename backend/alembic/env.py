from alembic import context
from vaultix.infrastructure.db import connect_engine

with connect_engine().connect() as connection:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()
