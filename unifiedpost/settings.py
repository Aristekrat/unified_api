from enum import Enum

ENV_LOCAL = 'local'
ENV_PROD = 'prod'
ENVS = {ENV_LOCAL, ENV_PROD, }

# tcp pool connections max limit
TCP_CONNECTIONS_LIMIT = 100

# keep DNS records in a cache for 1 hour to avoid DNS resolve before each request
TTL_DNS_CACHE = 60 * 60


DEFAULT_API_ARTICLES_LIMIT = 100


class Domain(Enum):
    """ All eligible domains """
    ABC = 'abcnews.go.com'
    BBC = 'bbc.com'
    BLOOMBERG = 'bloomberg.com'
    BUSINESS_INSIDER = 'businessinsider.com'
    CBS = 'cbsnews.com'
    CNBC = 'cnbc.com'
    CNN = 'us.cnn.com'
    CS_MONITOR = 'csmonitor.com'
    FORBES = 'forbes.com'
    FOX_NEWS = 'foxnews.com'
    NATIONAL_REVIEW = 'nationalreview.com'
    NPR = 'npr.org'
    NY_POST = 'nypost.com'
    NY_TIMES = 'nytimes.com'
    POLITICO = 'politico.com'
    REASON = 'reason.com'
    REUTERS = 'reuters.com'
    THE_AMERICAN_CONSERVATIVE = 'theamericanconservative.com'
    THE_ATLANTIC = 'theatlantic.com'
    THE_WEEK = 'theweek.com'
    USA_TODAY = 'usatoday.com'
    WASHINGTON_POST = 'washingtonpost.com'
    WSJ = 'wsj.com'


SOURCE_LEFT = 'left'
SOURCE_CENTER = 'center'
SOURCE_RIGHT = 'right'


# all domains by different sources
SOURCES = {
    SOURCE_LEFT: {
        Domain.NY_TIMES,
        Domain.NPR,
        Domain.POLITICO,
        Domain.REUTERS,
        Domain.THE_ATLANTIC,
        Domain.THE_WEEK,
        Domain.WASHINGTON_POST,
        Domain.CNN,
        Domain.BLOOMBERG,
        Domain.BUSINESS_INSIDER,
        Domain.FORBES,
        Domain.ABC
    },
    SOURCE_CENTER: {
        Domain.ABC,
        Domain.BBC,
        Domain.CBS,
        Domain.REUTERS,
        Domain.THE_WEEK,
        Domain.NATIONAL_REVIEW,
        Domain.NPR,
        Domain.CNBC,
        Domain.FORBES,
        Domain.BUSINESS_INSIDER,
        Domain.USA_TODAY,
        Domain.CS_MONITOR,
    },
    SOURCE_RIGHT: {
        Domain.FOX_NEWS,
        Domain.WSJ,
        Domain.NATIONAL_REVIEW,
        Domain.REUTERS,
        Domain.NY_POST,
        Domain.ABC,
        Domain.CBS,
        Domain.CNBC,
        Domain.REASON,
        Domain.THE_AMERICAN_CONSERVATIVE,
        Domain.CS_MONITOR,
    }
}

# domains for which `subscription = True` will be set
SUBSCRIPTION_ENABLED_DOMAINS = {
    Domain.NY_TIMES, Domain.WASHINGTON_POST, Domain.THE_ATLANTIC, Domain.WSJ
}

SOURCE_MAX_ARTICLES = 2000
