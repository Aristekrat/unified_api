import itertools
import json
import logging
import re
from typing import List, Dict
from urllib.parse import urlparse
from uuid import uuid4

from aiohttp import ClientSession
from aioredis import Redis

from settings import SOURCES, SOURCE_LEFT, SOURCE_RIGHT, SOURCE_CENTER
from .amp.google import create_amp_lookup
from .async_newsapi_client import (
    AsyncNewsAPIClient, NewsAPIError, NewsAPIThrottle, SubscriptionPlan
)

logger = logging.getLogger(__name__)


class NewsAPIParser:

    RE_EXTRA_CHARS_PATTERN = re.compile(r'\[\+\d+ chars\]')

    REDIS_PREFIX_RESULTS = 'parser:results'

    TARGET_LIST_LEFT = f'{REDIS_PREFIX_RESULTS}:left'
    TARGET_LIST_CENTER = f'{REDIS_PREFIX_RESULTS}:center'
    TARGET_LIST_RIGHT = f'{REDIS_PREFIX_RESULTS}:right'

    TARGET_LIST_BY_SOURCE_NAME = {
        SOURCE_LEFT: TARGET_LIST_LEFT,
        SOURCE_CENTER: TARGET_LIST_CENTER,
        SOURCE_RIGHT: TARGET_LIST_RIGHT
    }

    MAX_DOMAINS_PER_REQUEST = 20

    @staticmethod
    def _parse_domain(url):
        """ Parse and return a domain value without `www.` prefix from provided URL """
        _, domain, _, _, _, _ = urlparse(url)
        return domain.replace('www.', '')

    def __init__(self,
                 api_key,
                 plan: SubscriptionPlan,
                 redis_pool: Redis,
                 http_client: ClientSession,
                 domains: List[str]):

        # init API client
        self._news_api = AsyncNewsAPIClient(
            api_key=api_key,
            http_client=http_client
        )

        # init NewsAPI Throttler
        self._throttle = NewsAPIThrottle(plan=plan, redis_pool=redis_pool)

        self._redis_pool = redis_pool
        self._http_client = http_client
        self._parsed_urls = set()

        # divide input domains in a different scopes so we'll be able
        # to maximize the number of results per domain
        self._scope = []
        divider = len(domains) // self.MAX_DOMAINS_PER_REQUEST + 1
        interval = len(domains) // divider
        for x in range(divider):
            self._scope.append(domains[interval * x: interval * (x + 1)])

    def __str__(self):
        return self.__class__.__name__

    __repr__ = __str__

    async def init(self):
        """
        Initialize resources. Prepares everything before parsing
        """
        await self._throttle.init()

    async def run_forever(self):
        """ Entry point for parsing """
        logger.info(f'{self}: start parsing')

        for domains in itertools.cycle(self._scope):
            logger.debug(f'{self}: will parse {domains}')
            try:
                async with self._throttle:
                    await self._collect_parsed_urls()
                    try:
                        response = await self._news_api.everything(
                            domains=domains, page_size=100, language='en'
                        )
                    except NewsAPIError as e:
                        logger.exception(f"Error during fetching News API: {e}")
                        continue

                    amp_lookup = await self._construct_amp_lookup(response=response)
                    parsed_articles = self._parse_articles(response=response, amp_lookup=amp_lookup)
                    await self._persist_articles(articles=parsed_articles)

            except Exception:
                logger.exception(f'Unhandled error occurred during working with domains: {domains}')
                continue

    async def _collect_parsed_urls(self):
        """
        Iterate over all parsed lists and collect urls to avoid duplicates
        """
        logger.info(f'{self}: Collecting already parsed URLs. '
                    f'Current count is {len(self._parsed_urls)}')
        self._parsed_urls = set()

        for list_name in self.TARGET_LIST_BY_SOURCE_NAME.values():
            articles = await self._redis_pool.lrange(list_name, 0, -1)
            self._parsed_urls |= {json.loads(x)['url'] for x in articles}

        logger.info(f'{self}: Collected parsed URLs. Current count is {len(self._parsed_urls)}')

    async def _construct_amp_lookup(self, response: Dict) -> Dict:
        """
        Wrapper for constructing the AMP lookup dictionary.
        Currently uses only Google API
        """
        article_urls = {article['url'] for article in response['articles'] if article.get('url')}
        amp_lookup = await create_amp_lookup(urls=article_urls, http_client=self._http_client)
        return amp_lookup

    def _parse_articles(self,
                        response: Dict,
                        amp_lookup: Dict[str, str]) -> List[Dict]:
        """
        Parse articles. Apply normalization rules, do enrichment, etc
        """
        logger.info(f'{self}: Parsing articles')
        parsed_articles = []
        raw_articles = response['articles']

        for article in raw_articles:
            if article['url'] in self._parsed_urls:
                logger.debug(f'{self}: url {article["url"]} was already parsed')
                continue  # we've already parsed this article

            domain = self._parse_domain(article['url'])
            if not domain:
                logger.debug(f'{self}: cant parse article domain: {article}')
                continue  # we can't parse domain therefore we can't use this

            title = article.get('title', '') or ''
            description = article.get('description', title) or title
            content = article.get('content', description) or description

            parsed_article = {
                'uuid': str(uuid4()),
                'title': title,
                'author': article['author'],
                'description': description,
                'url': article['url'],
                'amp_url': amp_lookup.get(article['url']),
                'image_url': article['urlToImage'],
                'published_at': article['publishedAt'],
                'content': re.sub(self.RE_EXTRA_CHARS_PATTERN, '', content),
                'domain': domain
            }

            parsed_articles.append(parsed_article)

        logger.info(f'{self}: Parsed {len(parsed_articles)} out of {len(raw_articles)} articles')
        return parsed_articles

    # todo: this method potentially could be a completely separate service which could
    # todo: even be deployed to a different instance. Ideally parser should fire an
    # todo: event with a new article and one of the subscribers must persist it
    async def _persist_articles(self, articles: List[Dict]):
        """
        Persist articles to a redis lists
        """
        logger.info(f'{self}: persisting articles')
        final_articles = {SOURCE_LEFT: [], SOURCE_CENTER: [], SOURCE_RIGHT: []}
        for article in articles:
            domain = article.pop('domain', None)
            if not domain:
                continue
            for source_title, sources in SOURCES.items():
                if domain in sources:
                    final_articles[source_title].append(json.dumps(article))

            self._parsed_urls.add(article['url'])

        for source_title, articles in final_articles.items():
            if not articles:
                continue

            target_list = self.TARGET_LIST_BY_SOURCE_NAME[source_title]
            await self._redis_pool.lpush(target_list, *articles)

            # finally trim to 200 results per source
            await self._redis_pool.ltrim(target_list, 0, 2000)

        for source_title in SOURCES:
            logger.info(f'{self}: {len(final_articles[source_title])} '
                        f'articles persisted to {source_title}')

