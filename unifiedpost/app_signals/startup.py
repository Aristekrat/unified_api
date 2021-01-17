import logging
import os
import ssl

import aiohttp
import sentry_sdk
from aiohttp import ClientSession
from aiohttp.web_app import Application
from aiopg.sa import create_engine
from aioredis import create_redis_pool
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from settings import TCP_CONNECTIONS_LIMIT, TTL_DNS_CACHE

logger = logging.getLogger(__name__)


async def init_pg(app: Application):
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    db_host = os.environ['DB_HOST']
    db_name = os.environ['DB_NAME']

    dsn = f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}'
    app['db'] = await create_engine(
        dsn=dsn,
        minsize=1,
        maxsize=50,
        pool_recycle=3600
    )


async def init_sentry(app: Application):
    """
    Initialize sentry SDK for errors reporting
    """
    if app['debug'] is True:
        logger.warning('Sentry is not available in DEBUG envs')
        return

    sentry_dsn = os.environ.get('SENTRY_DSN')
    if not sentry_dsn:
        logger.warning('Missing Sentry DSN')
        return

    logger.info('Initializing sentry SDK')
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        integrations=[AioHttpIntegration(), SqlalchemyIntegration()],
        environment=app['env']
    )


async def init_redis_pool(app: Application):
    """
    Initialize shared redis pool. If SSL is enabled - we'll set it up
    with support for AWS ElastiCache to avoid cert verifying
    """
    host = os.environ.get('REDIS_HOST', 'localhost')
    port = os.environ.get('REDIS_PORT', 6379)

    dsn = f'redis://{host}:{port}'

    ssl_context = None
    if os.environ.get('REDIS_SSL', 'false') == 'true':
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    logger.info(f'Initializing redis pool with SSL {"enabled" if ssl_context else "disabled"}')
    app['redis_pool'] = await create_redis_pool(
        dsn,
        db=int(os.environ.get('REDIS_DB', 0)),
        password=os.environ.get('REDIS_PASSWORD'),
        ssl=ssl_context,
        encoding='utf-8',
        minsize=1,
        maxsize=10
    )


async def init_http_client(app: Application):
    """
    Initialize a shared HTTP client session.
    Custom TCP connector is used to speed up requests by avoiding DNS resolving each time
    """
    logger.info('Initializing HTTP client')
    tcp_connector = aiohttp.TCPConnector(limit=TCP_CONNECTIONS_LIMIT, ttl_dns_cache=TTL_DNS_CACHE)
    app['http_client'] = ClientSession(connector=tcp_connector)
