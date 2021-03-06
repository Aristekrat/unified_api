import json

from aiohttp.web_request import Request
from aiohttp_apispec import docs
from aioredis import Redis

from api.json_utils import json_200
from parsers.newsapi import NewsAPIParser
from settings import SOURCE_LEFT, SOURCE_CENTER, SOURCE_RIGHT, DEFAULT_API_ARTICLES_LIMIT


base_articles_doc = docs(
    summary='Articles API',
    description='Returns list of articles from appropriate sources (left, center of right)',
    parameters=[
        {
            'name': 'limit',
            'in': 'query',
            'default': 100,
            'type': 'integer',
            'description': 'Number of articles to be returned'
        }
    ],
    responses={
        200: {
            'description': 'list of articles',
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'uuid': {
                        'type': 'uuid'
                    },
                    'title': {
                        'type': 'string'
                    },
                    'author': {
                        'type': 'string'
                    },
                    'description': {
                        'type': 'string'
                    },
                    'url': {
                        'type': 'uri'
                    },
                    'amp_url': {
                        'type': 'uri'
                    },
                    'image_url': {
                        'type': 'uri'
                    },
                    'published_at': {
                        'type': 'string'
                    }
                }
            }
        }
    }
)


@base_articles_doc
async def view_get_left(request: Request):
    """ Return all news from `left` list """
    return await view_get_from_base_list(request, SOURCE_LEFT)


@base_articles_doc
async def view_get_center(request: Request):
    """ Return all news from `center` list """
    return await view_get_from_base_list(request, SOURCE_CENTER)


@base_articles_doc
async def view_get_right(request: Request):
    """ Return all news from `right` list """
    return await view_get_from_base_list(request, SOURCE_RIGHT)


async def view_get_from_base_list(request: Request, suffix: str):
    """
    Return all news from list with provided `suffix`
    """
    try:
        limit = int(request.query.get('limit'))
    except (TypeError, ValueError):
        limit = DEFAULT_API_ARTICLES_LIMIT

    redis_pool: Redis = request.config_dict['redis_pool']

    # get all articles
    target_list_key = f'{NewsAPIParser.REDIS_PREFIX_RESULTS}:{suffix}'
    raw_articles = await redis_pool.lrange(target_list_key, 0, limit - 1)

    # serialize and return
    articles = [json.loads(article) for article in raw_articles]
    return json_200(articles)
