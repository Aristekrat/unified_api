from aiohttp.web_app import Application
from .views import view_get_left, view_get_center, view_get_right


def setup_routes(app: Application):
    app.router.add_get('/left', view_get_left)
    app.router.add_get('/center', view_get_center)
    app.router.add_get('/right', view_get_right)
