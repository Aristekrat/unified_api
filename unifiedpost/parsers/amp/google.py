import logging
import os
from typing import Dict, Collection, Optional

from aiohttp import ClientSession


logger = logging.getLogger(__name__)


GOOGLE_AMP_MAX_URLS = 50
STRATEGY_FETCH_LIVE_DOCS = 'FETCH_LIVE_DOC'
STRATEGY_IN_INDEX_DOC = 'IN_INDEX_DOC'
AMP_BATCH_GET_URL = 'https://acceleratedmobilepageurl.googleapis.com/v1/ampUrls:batchGet'


async def create_amp_lookup(urls: Collection[str],
                            lookup_strategy: str = STRATEGY_FETCH_LIVE_DOCS,
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
    for x in range(len(urls) - 1 // GOOGLE_AMP_MAX_URLS + 1):
        start_idx = x * GOOGLE_AMP_MAX_URLS
        end_idx = x * GOOGLE_AMP_MAX_URLS + GOOGLE_AMP_MAX_URLS
        scope = urls[start_idx:end_idx]

        if not scope:
            continue

        async with http_client.post(
            AMP_BATCH_GET_URL,
            json={'urls': scope, 'lookupStrategy': lookup_strategy},
            params={'key': os.environ['GOOGLE_API_KEY']}
        ) as response:
            json_response = await response.json()
            lookup.update({x['originalUrl']: x['ampUrl'] for x in json_response['ampUrls']})

    logger.info(f'AMP lookup created. Found {len(lookup)} out of {len(urls)} URLs')
    return lookup
