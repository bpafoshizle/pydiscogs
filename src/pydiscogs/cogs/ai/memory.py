import logging
from typing import AsyncGenerator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)


async def get_postgres_saver(db_url: str) -> AsyncGenerator[AsyncPostgresSaver, None]:
    """
    Returns an AsyncPostgresSaver instance for LangGraph checkpointing.
    """
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    async with AsyncConnectionPool(
        conninfo=db_url,
        max_size=10,
        kwargs=connection_kwargs,
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        # Ensure tables are created
        await checkpointer.setup()
        yield checkpointer


async def get_postgres_store(db_url: str) -> AsyncGenerator[AsyncPostgresStore, None]:
    """
    Returns an AsyncPostgresStore instance for LangGraph long-term memory.
    """
    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }
    async with AsyncConnectionPool(
        conninfo=db_url,
        max_size=10,
        kwargs=connection_kwargs,
    ) as pool:
        store = AsyncPostgresStore(pool)
        # Ensure tables are created
        await store.setup()
        yield store
