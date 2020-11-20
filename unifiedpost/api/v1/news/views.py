import json

from aiohttp.web_request import Request
from aioredis import Redis

from api.json_utils import json_200
from settings import SOURCE_LEFT, SOURCE_CENTER, SOURCE_RIGHT


async def view_get_left(request: Request):
    return await view_get_from_base_list(request, SOURCE_LEFT)


async def view_get_center(request: Request):
    return await view_get_from_base_list(request, SOURCE_CENTER)


async def view_get_right(request: Request):
    return await view_get_from_base_list(request, SOURCE_RIGHT)


async def view_get_from_base_list(request: Request, suffix: str):
    redis_pool: Redis = request.config_dict['redis_pool']
    raw_articles = await redis_pool.lrange(f'parser:results:{suffix}', 0, 200)
    articles = [json.loads(article) for article in raw_articles]
    return json_200({suffix: articles})
