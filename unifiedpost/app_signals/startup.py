import asyncio
import logging
import os
import ssl

import aiohttp
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from aiohttp import ClientSession
from aiohttp.web_app import Application
from aioredis import create_redis_pool

from parsers.async_newsapi_client import SubscriptionPlan
from parsers.newsapi import NewsAPIParser
from settings import DOMAINS_LIST, TCP_CONNECTIONS_LIMIT, TTL_DNS_CACHE

logger = logging.getLogger(__name__)


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
        integrations=[AioHttpIntegration()]
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


async def init_news_api_parser(app: Application):
    """ NewsAPI parser task """
    logger.info('Initializing NewsAPI parser')
    redis_pool = app['redis_pool']
    http_client = app['http_client']

    app['news_api_parser'] = news_api_parser = NewsAPIParser(
        api_key=os.environ['NEWSAPI_API_KEY'],
        plan=SubscriptionPlan.DEVELOPER,
        redis_pool=redis_pool,
        http_client=http_client,
        domains=DOMAINS_LIST
    )

    await news_api_parser.init()
    app['news_api_task'] = asyncio.create_task(news_api_parser.run_forever())
