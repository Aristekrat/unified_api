import asyncio
import logging
import os
import ssl

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from aiohttp import ClientSession
from aiohttp.web_app import Application
from aioredis import create_redis_pool

from parsers.async_newsapi_client import SubscriptionPlan
from parsers.newsapi import NewsAPIParser
from settings import DOMAINS_LIST

logger = logging.getLogger(__name__)


async def init_sentry(app: Application):
    """
    Initialize sentry SDK for errors reporting
    """

    if app['debug'] is True:
        logger.warning('Sentry is not available in DEBUG envs')
        return

    sentry_sdk.init(
        "https://af21206c87c7485fbce4d34cf1e60f74@o478934.ingest.sentry.io/5523585",
        traces_sample_rate=1.0,
        integrations=[AioHttpIntegration()]
    )


async def init_redis_pool(app: Application):
    dsn = f'redis://{os.environ["REDIS_HOST"]}:{os.environ["REDIS_PORT"]}'

    if os.environ.get('REDIS_SSL') is None:
        ssl_context = None

    else:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False

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
    app['http_client'] = ClientSession()


async def init_news_api_parser(app: Application):
    app['news_api_parser'] = news_api_parser = NewsAPIParser(
        api_key=os.environ['NEWSAPI_API_KEY'],
        plan=SubscriptionPlan.DEVELOPER,
        redis_pool=app['redis_pool'],
        http_client=app['http_client'],
        domains=DOMAINS_LIST
    )

    await news_api_parser.init()
    asyncio.create_task(news_api_parser.run_forever())
