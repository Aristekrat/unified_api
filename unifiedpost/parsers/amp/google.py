import logging
import os
from enum import Enum
from typing import Dict, Collection, Optional

from aiohttp import ClientSession


logger = logging.getLogger(__name__)


BATCH_MAX_URLS = 50
API_URL = 'https://acceleratedmobilepageurl.googleapis.com/v1/ampUrls:batchGet'


class LookupStrategy(Enum):
    """
    AMP lookup strategies:

    FETCH_LIVE_DOC:
        strategy involves live document fetch of URLs not found in the index.
        Any request URL not found in the index is crawled in realtime to validate if there
        is a corresponding AMP URL. This strategy has higher coverage but with extra latency
        introduced by realtime crawling. This is the default strategy. Applications using this
        strategy should set higher HTTP timeouts of the API calls.

    IN_INDEX_DOC:
        strategy skips fetching live documents of URL(s) not found in index. For
        applications which need low latency use of IN_INDEX_DOC strategy is recommended.

    """
    FETCH_LIVE_DOC = 'FETCH_LIVE_DOC'
    IN_INDEX_DOC = 'IN_INDEX_DOC'


async def create_amp_lookup(urls: Collection[str],
                            lookup_strategy: LookupStrategy = LookupStrategy.FETCH_LIVE_DOC,
                            http_client: Optional[ClientSession] = None) -> Dict:
    """
    Creates an AMP lookup dict based on provided articles.
    Do a google API call and tries to match existing articles urls
    to AMP versions. Returns a dict where key is an original url
    and value is an AMP url
    """
    logger.info('Creating AMP lookup')
    if not urls:
        return {}

    urls = list(urls)  # convert to list so we'll be able to do a slicing
    http_client = http_client or ClientSession()
    lookup = {}

    # since max number of URLs we can pass is 50 - we divide the urls
    # list into a few different lists to be able to process all of them
    for x in range(len(urls) - 1 // BATCH_MAX_URLS + 1):
        start_idx = x * BATCH_MAX_URLS
        end_idx = x * BATCH_MAX_URLS + BATCH_MAX_URLS
        scope = urls[start_idx:end_idx]

        if not scope:
            continue

        async with http_client.post(
            API_URL,
            json={'urls': scope, 'lookupStrategy': lookup_strategy.value},
            params={'key': os.environ['GOOGLE_API_KEY']}
        ) as response:

            response.raise_for_status()
            json_response = await response.json()
            amp_urls = json_response.get('ampUrls')
            if not amp_urls:
                continue  # it's possible that no AMP URL's returned
            lookup.update({x['originalUrl']: x['ampUrl'] for x in amp_urls})

    logger.info(f'AMP lookup created. Found {len(lookup)} out of {len(urls)} URLs')
    return lookup
