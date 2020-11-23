ENV_LOCAL = 'local'
ENV_PROD = 'prod'
ENVS = {ENV_LOCAL, ENV_PROD, }

# tcp pool connections max limit
TCP_CONNECTIONS_LIMIT = 100

# keep DNS records in a cache for 1 hour to avoid DNS resolve before each request
TTL_DNS_CACHE = 60 * 60

SOURCE_LEFT = 'left'
SOURCE_CENTER = 'center'
SOURCE_RIGHT = 'right'

SOURCES = {
    SOURCE_LEFT: {
        'nytimes.com',
        'npr.org',
        'politico.com',
        'reuters.com',
        'theatlantic.com',
        'theweek.com',
        'washingtonpost.com',
        'us.cnn.com',
        'bloomberg.com',
        'businessinsider.com',
        'forbes.com',
        'abcnews.go.com',
    },
    SOURCE_CENTER: {
        'abcnews.go.com',
        'bbc.com',
        'cbsnews.com',
        'reuters.com',
        'theweek.com',
        'nationalreview.com',
        'npr.org',
        'cnbc.com',
        'forbes.com',
        'businessinsider.com',
        'usatoday.com',
        'csmonitor.com',
    },
    SOURCE_RIGHT: {
        'foxnews.com',
        'wsj.com',
        'nationalreview.com',
        'reuters.com',
        'nypost.com',
        'abcnews.go.com',
        'cbsnews.com',
        'cnbc.com',
        'reason.com',
    }
}

SUBSCRIPTION_AVAILABLE_SOURCES = {
    'nytimes.com', 'washingtonpost.com', 'theatlantic.com',
}

SOURCES_SET = {source for sources in SOURCES.values() for source in sources}
DOMAINS_LIST = sorted(SOURCES_SET)
