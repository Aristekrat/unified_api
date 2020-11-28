import datetime
import itertools
import json
import logging
import random
import re
from asyncio import CancelledError
from typing import List, Dict
from urllib.parse import urlparse
from uuid import uuid4

from aiohttp import ClientSession
from aioredis import Redis

from settings import SOURCES, SOURCE_LEFT, SOURCE_RIGHT, SOURCE_CENTER, \
    SUBSCRIPTION_ENABLED_DOMAINS, SOURCE_MAX_ARTICLES
from .amp.google import create_amp_lookup
from .async_newsapi_client import (
    AsyncNewsAPIClient, NewsAPIError, NewsAPIThrottle, SubscriptionPlan
)

logger = logging.getLogger(__name__)


class NewsAPIParser:
    """
    NewsAPI parser. Utilize newsapi client to fetch the news.
    """

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

    DATE_FORMAT = '%B %d, %Y %I:%M %p'

    @staticmethod
    def _parse_domain(url):
        """ Parse and return a domain from a provided URL. Also trims the `www.` prefix """
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
        self._domains = domains
        self._parsed_urls = set()
        self._domains_chunks = []

    def __str__(self):
        return self.__class__.__name__

    __repr__ = __str__

    async def init(self):
        """
        Initialize resources. Prepares everything before parsing
        """
        await self._throttle.init()

    async def run_forever(self):
        """ Main parsing task """
        try:
            logger.info(f'{self}: running forever...')
            while True:
                self._shuffle_domains()
                for chunk in self._domains_chunks:
                    await self._process_chunk(chunk)

        except CancelledError:
            logger.warning(f'{self}: `run_forever` task was cancelled')
            return

        except Exception as e:
            logger.exception(f'{self}: Unhandled error occurred in `run_forever` task')
            raise e

    def _shuffle_domains(self):
        """
        Randomly shuffles domains scope, e.g. let's imagine that we have
        domains A, B, C and D and we divide them into a 2 chunks - [[A, B], [C, D]].
        Max number of results from API is 100, so it's possible that for chunk
        [A, B] - we'll have 100 results from source `A` and 0 results from source `B`.
        Shuffling will help us to solve this kind of situation during the next API call,
        let's say in the next call if the chunk will be different, e.g. [B, C] - we'll
        potentially have much more results for source `B`.
        Overall idea - we want to maximize the numbers of results from API on a long run
        """
        random.shuffle(self._domains)
        self._domains_chunks = [[] for _ in range(self._throttle.n_calls_per_hour)]
        for index, domain in zip(
            itertools.cycle(range(self._throttle.n_calls_per_hour)),
            self._domains
        ):
            self._domains_chunks[index].append(domain)

    async def _process_chunk(self, domains: List[str]):
        """
        Processing of a single chunk of domains.
        """
        logger.debug(f'{self}: parsing {domains}')
        try:
            async with self._throttle:
                await self._collect_parsed_urls()
                try:
                    response = await self._news_api.everything(
                        domains=domains,
                        page_size=100,
                        language='en'
                    )
                except NewsAPIError as e:
                    logger.exception(f"{self}: Error during fetching News API: {e}")
                    return

                articles = response['articles']
                articles = list(self._gen_eligible_articles(articles=articles))
                amp_lookup = await self._construct_amp_lookup(articles=articles)
                articles = self._parse_articles(articles=articles, amp_lookup=amp_lookup)
                await self._persist_articles(articles=articles)

        except CancelledError as e:
            raise e  # propagate

        except Exception:
            logger.exception(
                f'{self}: Unhandled error occurred during parsing domains: {domains}'
            )
            return

    async def _collect_parsed_urls(self):
        """
        Iterate over all existing lists and collect urls to avoid future duplicates
        """
        logger.info(f'{self}: Collecting already parsed URLs')
        self._parsed_urls = set()

        for list_name in self.TARGET_LIST_BY_SOURCE_NAME.values():
            articles = await self._redis_pool.lrange(list_name, 0, -1)
            self._parsed_urls |= {json.loads(x)['url'] for x in articles}

        logger.info(f'{self}: Collected parsed URLs. Current count is {len(self._parsed_urls)}')

    def _gen_eligible_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Yield only "eligible" articles based on input scope and rules:
        - If article was already parsed - we'll filter it out.
        - If article domain couldn't be parsed - filter out
        """
        for article in articles:

            # check if we've already parsed this article
            if article['url'] in self._parsed_urls:
                logger.debug(f'{self}: url {article["url"]} was already parsed')
                continue

            # check if domain is "parsable"
            domain = self._parse_domain(article['url'])
            if not domain:
                logger.debug(f'{self}: cant parse article domain: {article}')
                continue

            yield article

    async def _construct_amp_lookup(self, articles: List[Dict]) -> Dict:
        """
        Wrapper for constructing the AMP lookup dictionary.
        Currently uses only Google API
        """
        article_urls = {article['url'] for article in articles if article.get('url')}
        if not article_urls:
            return {}
        amp_lookup = await create_amp_lookup(urls=article_urls, http_client=self._http_client)
        return amp_lookup

    def _parse_articles(self,
                        articles: List[Dict],
                        amp_lookup: Dict[str, str]) -> List[Dict]:
        """
        Parse articles. Apply normalization rules, do enrichment, etc
        """
        logger.info(f'{self}: Parsing articles')
        parsed_articles = []

        for article in articles:
            article_domain = self._parse_domain(article['url'])
            title = article.get('title', '') or ''
            description = article.get('description', title) or title
            content = article.get('content', description) or description
            published_at = datetime.datetime.strptime(
                article['publishedAt'], AsyncNewsAPIClient.DATE_FORMAT
            ).strftime(self.DATE_FORMAT)

            parsed_article = {
                'uuid': str(uuid4()),
                'source': article['source'],
                'title': title,
                'author': article['author'],
                'description': description,
                'url': article['url'],
                'amp_url': amp_lookup.get(article['url']),
                'image_url': article['urlToImage'],
                'published_at': published_at,
                'content': re.sub(self.RE_EXTRA_CHARS_PATTERN, '', content),
                'domain': article_domain,
                'subscription': False
            }

            # change `subscription` property for needed domains
            for domain in SUBSCRIPTION_ENABLED_DOMAINS:
                if domain.value in article_domain:
                    parsed_article['subscription'] = True
                    break

            parsed_articles.append(parsed_article)

        logger.info(f'{self}: Parsed {len(parsed_articles)} out of {len(articles)} articles')
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
            article_domain = article.pop('domain', None)
            if not article_domain:
                continue
            for source_title, sources in SOURCES.items():
                # we iterate over source names to be able to include the subdomains news
                for source in sources:
                    if source in article_domain:
                        final_articles[source_title].append(json.dumps(article))
                        break

            self._parsed_urls.add(article['url'])

        for source_title, articles in final_articles.items():
            if not articles:
                continue

            target_list = self.TARGET_LIST_BY_SOURCE_NAME[source_title]
            await self._redis_pool.lpush(target_list, *articles)

            # finally trim to `max_articles` results per source
            await self._redis_pool.ltrim(target_list, 0, SOURCE_MAX_ARTICLES)

        for source_title in SOURCES:
            logger.info(
                f'{self}: {len(final_articles[source_title])} articles persisted to {source_title}'
            )

