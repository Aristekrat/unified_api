import asyncio
import logging

from aiohttp.web_app import Application
from aiopg.sa import Engine

logger = logging.getLogger(__name__)


async def close_pg(app: Application):
    db: Engine = app['db']
    db.close()
    await db.wait_closed()


async def close_redis_pool(app: Application):
    """ Shutdown redis pool """
    logger.info('Shutting down redis pool')
    redis_pool = app['redis_pool']
    redis_pool.close()
    await redis_pool.wait_closed()


async def close_http_client(app: Application):
    """ Shutdown a requests client session """
    logger.info('Shutting down HTTP client')
    http_client = app['http_client']
    await http_client.close()

    # Wait 500 ms for the underlying SSL connections to close
    await asyncio.sleep(0.500)
