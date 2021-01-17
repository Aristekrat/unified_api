from aiohttp.web_request import Request
from aiohttp_apispec import docs

from api.json_utils import json_200
from db.utils import fetchall
from settings import SOURCE_LEFT, SOURCE_CENTER, SOURCE_RIGHT

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
        },
        {
            'name': 'max_id',
            'in': 'query',
            'default': None,
            'type': 'integer',
            'description': 'Article identifier which will be used to return a "next" '
                           'portion of articles which has id lower than provided one'
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
        limit = request.config_dict['config']['api']['articles_default_limit']

    try:
        # filter using provided article id. get all articles
        # which were published BEFORE the provided one. Used
        # for a `next page` functionality
        max_id = int(request.query.get('max_id'))
        max_id_filter_statement = f"""
            AND published_at < (
                SELECT published_at 
                FROM articles_{suffix} 
                WHERE id = {max_id}
            )
        """

    except (TypeError, ValueError):
        max_id_filter_statement = ''

    days_interval = request.config_dict['config']['api']['articles_days_interval']
    days_interval_statement = f"AND published_at >= now() - interval '{days_interval} days'"

    query = f"""
        SELECT * 
        FROM articles_{suffix}
        WHERE 1 = 1 
        {days_interval_statement}
        {max_id_filter_statement}
        ORDER BY published_at DESC
        LIMIT {limit}
    """

    engine = request.config_dict['db']
    async with engine.acquire() as conn:
        articles = await fetchall(conn=conn, query=query)

    return json_200(articles)
