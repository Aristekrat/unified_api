ENV_LOCAL = 'local'
ENV_PROD = 'prod'
ENVS = {ENV_LOCAL, ENV_PROD, }

# tcp pool connections max limit
TCP_CONNECTIONS_LIMIT = 100

# keep DNS records in a cache for 1 hour to avoid DNS resolve before each request
TTL_DNS_CACHE = 60 * 60


DEFAULT_API_ARTICLES_LIMIT = 100

DATE_FORMAT = '%B %d, %Y %I:%M %p'

SOURCE_LEFT = 'left'
SOURCE_CENTER = 'center'
SOURCE_RIGHT = 'right'
