from aiohttp.web_app import Application
from .views import view_get_healthcheck


def setup_common_api_routes(app: Application):
    app.router.add_get('/health', view_get_healthcheck)
