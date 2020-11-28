import logging

from aiohttp.web_app import Application
from aiohttp_apispec import setup_aiohttp_apispec

from api.routes import setup_common_api_routes
from api.v1.news import create_news_v1_app
from app_signals.shutdown import close_redis_pool, close_http_client
from .app_signals.startup import (
    init_redis_pool, init_http_client, init_news_api_parser, init_sentry
)


logger = logging.getLogger(__name__)


def create_app(args, debug: bool = False) -> Application:
    """
    Entry-point for `Application` instance creation
    """
    logger.info(f'Initializing app for {args.env}. Debug mode is {"on" if debug else "off"}')

    app = Application()
    app['env'] = args.env
    app['debug'] = debug

    # common routes
    setup_common_api_routes(app)

    # v1 routes
    app.add_subapp('/api/v1/news', create_news_v1_app())

    # Swagger
    if debug is True:
        setup_aiohttp_apispec(
            app=app,
            title='UnifiedPost API',
            version='v1',
            swagger_path='/apidocs'
        )

    # startup and shutdown signals
    app.on_startup.extend([init_redis_pool, init_http_client, init_sentry])
    app.on_shutdown.extend([close_redis_pool, close_http_client])

    if not args.disable_parser:
        app.on_startup.append(init_news_api_parser)

    return app
