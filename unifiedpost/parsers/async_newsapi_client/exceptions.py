class Retry(Exception):
    """ Retry error which is used for backoff """


class NewsAPIError(Exception):
    """ Base NewsAPI Error """
    def __init__(self, status, code, message):
        self.status = status
        self.code = code
        self.message = message

    def __str__(self):
        return f'NewsAPIError {self.code}: {self.message}'

    __repr__ = __str__
