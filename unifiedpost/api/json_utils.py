import datetime
import json
from functools import partial

from aiohttp import web
from aiohttp.web_exceptions import HTTPOk, HTTPBadRequest

from settings import DATE_FORMAT


def datetime_serializer(o):
    """ Serialize a datetime object to a string """
    if isinstance(o, (datetime.date, datetime.datetime, )):
        return o.strftime(DATE_FORMAT)


with_datetime_dumps = partial(json.dumps, default=datetime_serializer)
base_response = partial(web.json_response, dumps=with_datetime_dumps)
json_200 = partial(base_response, status=HTTPOk.status_code)
json_400 = partial(base_response, status=HTTPBadRequest.status_code)
