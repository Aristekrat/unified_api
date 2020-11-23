import json

from aiohttp.web_request import Request
from aioredis import Redis

from api.json_utils import json_200
from parsers.newsapi import NewsAPIParser
from settings import SOURCE_LEFT, SOURCE_CENTER, SOURCE_RIGHT


async def view_get_left(request: Request):
    """ Return all news from `left` list """
    return await view_get_from_base_list(request, SOURCE_LEFT)


async def view_get_center(request: Request):
    """ Return all news from `center` list """
    return await view_get_from_base_list(request, SOURCE_CENTER)


async def view_get_right(request: Request):
    """ Return all news from `right` list """
    return await view_get_from_base_list(request, SOURCE_RIGHT)


async def view_get_from_base_list(request: Request, suffix: str):
    """
    Return all news from list with provided `suffix`
    """
    redis_pool: Redis = request.config_dict['redis_pool']
    # get all articles
    target_list_key = f'{NewsAPIParser.REDIS_PREFIX_RESULTS}:{suffix}'
    raw_articles = await redis_pool.lrange(target_list_key, 0, -1)

    # serialize and return
    articles = [json.loads(article) for article in raw_articles]
    return json_200({suffix: articles})
