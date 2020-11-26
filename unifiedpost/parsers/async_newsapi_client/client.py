import asyncio
import logging
from time import time
from typing import Optional, List, Dict

import backoff
from aiohttp import ClientSession, ClientResponseError, ContentTypeError
from aioredis import Redis

from .constants import SubscriptionPlan, RESPONSE_OK
from .exceptions import Retry, NewsAPIError


logger = logging.getLogger(__name__)


class AsyncNewsAPIClient:
    """
    Asynchronous wrapper for https://newsapi.org
    """

    BASE_URL = 'https://newsapi.org/v2'
    DATE_FORMAT = '%Y-%m-%dT%H:%S:%MZ'

    def __init__(self,
                 api_key: str,
                 http_client: Optional[ClientSession]):

        self._api_key = api_key
        self._http_client = http_client or ClientSession()

    def __str__(self):
        return self.__class__.__name__

    __repr__ = __str__

    @property
    def headers(self):
        """ Base headers used for auth """
        return {'X-Api-Key': self._api_key}

    async def everything(self,
                         q: Optional[str] = None,
                         qln_title: Optional[str] = None,
                         sources: Optional[List[str]] = None,
                         domains: Optional[List[str]] = None,
                         exclude_domains: Optional[List[str]] = None,
                         date_from: Optional[str] = None,
                         date_to: Optional[str] = None,
                         language: Optional[str] = None,
                         sort_by: Optional[str] = None,
                         page_size: Optional[float] = None,
                         page: Optional[int] = None) -> Dict:
        """
        :param q: Keywords or phrases to search for in the article title and body.
                  Advanced search is supported here:
                  - Surround phrases with quotes (") for exact match.
                  - Prepend words or phrases that must appear with a + symbol. Eg: +bitcoin
                  - Prepend words that must not appear with a - symbol. Eg: -bitcoin
                  - Alternatively you can use the AND / OR / NOT keywords, and optionally group
                    these with parenthesis. Eg: crypto AND (ethereum OR litecoin) NOT bitcoin.
        :param qln_title: Keywords or phrases to search for in the article title only.
                          Advanced search is supported here:
                          - Surround phrases with quotes (") for exact match.
                          - Prepend words or phrases that must appear with a + symbol. Eg: +bitcoin
                          - Prepend words that must not appear with a - symbol. Eg: -bitcoin
                          – Alternatively you can use the AND / OR / NOT keywords, and optionally
                            group these with parenthesis. Eg: crypto AND (ethereum OR litecoin)
                            NOT bitcoin.
        :param sources: A list of strings of identifiers (maximum 20) for the news sources or
                        blogs you want headlines from. Use the /sources endpoint to locate these
                        programmatically or look at the sources index.
        :param domains: A list of strings of domains (eg bbc.co.uk, techcrunch.com,
                        engadget.com) to restrict the search to.
        :param exclude_domains: A list of strings of domains (eg bbc.co.uk, techcrunch.com,
                                engadget.com) to remove from the results.
        :param date_from: Datetime for the `oldest` article allowed.
        :param date_to: Datetime for the `newest` article allowed.
        :param language: The 2-letter ISO-639-1 code of the language you want to get headlines for.
                         Possible options: ar, de, en, es, fr, he, it, nl, no, pt, ru, se, ud, zh.
                         Default: all languages returned.
        :param sort_by: The order to sort the articles in. Possible options: `relevancy`,
                        `popularity`, `publishedAt`.
                        `relevancy` = articles more closely related to q come first.
                        `popularity` = articles from popular sources and publishers come first.
                        `publishedAt` = newest articles come first.
                        Default: `publishedAt`
        :param page_size: The number of results to return per page.
                          `20` is the default, `100` is the maximum.
        :param page: Use this to page through the results.
        """
        params = {}
        if q is not None:
            params['q'] = q

        if qln_title is not None:
            params['qInTitle'] = qln_title

        if sources is not None:
            params['sources'] = ','.join(sources)

        if domains is not None:
            params['domains'] = ','.join(domains)

        if exclude_domains is not None:
            params['excludeDomains'] = ','.join(exclude_domains)

        if date_from is not None:
            params['from'] = date_from

        if date_to is not None:
            params['to'] = date_to

        if language is not None:
            params['language'] = language

        if sort_by is not None:
            params['sortBy'] = sort_by

        if page_size is not None:
            params['pageSize'] = page_size

        if page is not None:
            params['page'] = page

        return await self._base_request(endpoint='everything', params=params)

    @backoff.on_exception(
        wait_gen=backoff.expo,
        exception=(Retry, asyncio.TimeoutError)
    )
    async def _base_request(self, endpoint: str, params: Dict) -> Dict:
        """ Base request wrapper """
        url = f'{self.BASE_URL}/{endpoint}'
        async with self._http_client.get(url,
                                         params=params,
                                         headers=self.headers) as response:
            try:
                response.raise_for_status()
            except ClientResponseError as e:
                if e.status >= 500:
                    raise Retry()
                else:
                    # 400 <= status < 500
                    message = await response.text()
                    raise NewsAPIError(status=e.status,
                                       code=e.status,
                                       message=message)

            try:
                json_response = await response.json()
            except ContentTypeError as e:
                logger.exception(f'{self}: Malformed JSON returned')
                raise e

            if json_response['status'] != RESPONSE_OK:
                raise NewsAPIError(
                    status=json_response['status'],
                    code=json_response['code'],
                    message=json_response['message']
                )
            return json_response


class NewsAPIThrottle:
    """
    Throttling context manager for News API. Responsible for
    persisting and determination of a call time and invokes
    a `sleep` if necessary. Works on top of Redis

    Example usage:
    >>> newsapi: AsyncNewsAPIClient = ...
    >>> redis_pool: Redis = ...
    >>>
    >>> throttle = NewsAPIThrottle(plan=SubscriptionPlan.DEVELOPER, redis_pool=redis_pool)
    >>> await throttle.init()
    >>> async with throttle:
    >>>     await newsapi.everything(...)
    """

    LCA_REDIS_KEY = 'newsapi:throttle:last_call_at'

    def __init__(self,
                 plan: SubscriptionPlan,
                 redis_pool: Optional[Redis] = None):
        # number of calls per hour based on a plan
        self.n_calls_per_hour = plan.value // 24
        # interval between calls based on a plan. seconds
        self._sleep_interval = 24 * 60 * 60 / plan.value + 1
        self._redis_pool = redis_pool
        self._last_call_at = None

    def __str__(self):
        return self.__class__.__name__

    __repr__ = __str__

    async def init(self):
        """ Initialize Throttler in case if redis pool was providded. """
        if self._redis_pool is not None:
            last_call_at = await self._redis_pool.get(self.LCA_REDIS_KEY)
            self._last_call_at = float(last_call_at) if last_call_at else None

    async def __aenter__(self):
        """
        Determines for how long we should sleep before proceed
        """
        if self._last_call_at is not None:
            sleep_for = (self._sleep_interval + self._last_call_at) - time()
            logger.debug(f'{self}: Throttling for {sleep_for}')
            await asyncio.sleep(sleep_for)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        persist last call time which'll be used during next iteration
        """
        now = time()
        self._last_call_at = now
        await self._redis_pool.set(self.LCA_REDIS_KEY, now)
        if exc_type:
            return False  # re-raise
