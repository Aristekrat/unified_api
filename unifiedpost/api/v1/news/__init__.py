from aiohttp.web_app import Application

from .routes import setup_routes


def create_news_v1_app():
    app = Application()
    setup_routes(app)
    return app
