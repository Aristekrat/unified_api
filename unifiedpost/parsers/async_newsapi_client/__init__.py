import asyncio
import json
import logging
from dataclasses import dataclass
from enum import IntEnum
from time import time
from typing import Optional, List, Dict

import backoff
from aiohttp import ClientSession, ClientResponseError, ContentTypeError
from aioredis import Redis


__all__ = ('NewsAPIError', 'AsyncNewsAPIClient', 'NewsAPIThrottle', 'SubscriptionPlan')


logger = logging.getLogger(__name__)


class SubscriptionPlan(IntEnum):
    DEVELOPER = 100
    BUSINESS = 250000
    ENTERPRISE = 250000


class NewsAPIError(Exception):
    """ Base NewsAPI Error """
    def __init__(self, status, code, message):
        self.status = status
        self.code = code
        self.message = message

    def __str__(self):
        return f'NewsAPIError {self.code}: {self.message}'

    __repr__ = __str__


class Retry(Exception):
    """ Retry error which is used for backoff """


@dataclass
class Article:
    pass


class NewsAPIThrottle:
    """
    Throttling context manager for News API.
    Responsible for persisting and determination of a call time and invokes a `sleep` if necessary
    Usage:

    >>> throttle = NewsAPIThrottle(plan=SubscriptionPlan.DEVELOPER, redis_pool=pool)
    >>> await throttle.init()
    >>> async with throttle:
    >>>     newsapi.everything(...)
    """

    LCA_REDIS_KEY = 'newsapi:throttle:last_call_at'

    def __init__(self,
                 plan: SubscriptionPlan,
                 redis_pool: Optional[Redis] = None):

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


class AsyncNewsAPIClient:

    _BASE_URL = 'https://newsapi.org/v2'

    def __init__(self,
                 api_key: str,
                 http_client: Optional[ClientSession],
                 return_mock_response: bool = False):

        self._api_key = api_key
        self._http_client = http_client or ClientSession()
        self._return_mock_response = return_mock_response

    @property
    def headers(self):
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
            params['excludeDomains'] = exclude_domains

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
        if self._return_mock_response is True:
            with open('unifiedpost/async_newsapi_client/mocked_response.json') as f:
                return json.load(f)

        url = f'{self._BASE_URL}/{endpoint}'
        async with self._http_client.get(url,
                                         params=params,
                                         headers=self.headers) as response:
            try:
                response.raise_for_status()
            except ClientResponseError as e:
                if e.status >= 500:
                    raise Retry()
                # todo: 401 doesn't contain JSON response

            try:
                json_response = await response.json()
            except ContentTypeError as e:
                logger.exception(e)
                raise e

            if json_response['status'] != 'ok':
                raise NewsAPIError(
                    status=json_response['status'],
                    code=json_response['code'],
                    message=json_response['message']
                )
            return json_response
