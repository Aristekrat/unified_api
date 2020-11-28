from functools import partial

from aiohttp.web_response import json_response


# simple wrappers for json response
json_200 = partial(json_response, status=200)
json_400 = partial(json_response, status=400)
