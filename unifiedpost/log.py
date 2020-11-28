import logging
from logging.config import dictConfig


def setup_logging(debug: bool = False):
    """ Init project logging """
    level = logging.DEBUG if debug is True else logging.INFO
    dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'handlers': {
            'default': {
                'level': level,
                'formatter': 'standard',
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stderr',
            },
        },
        'loggers': {
            logger_name: {
                'handlers': ['default'],
                'level': level,
                'propagate': False
            } for logger_name in ('unifiedpost', 'api', 'parsers')
        }
    })
