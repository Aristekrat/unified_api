from datetime import datetime

from aiohttp.web_request import Request

from api.json_utils import json_200


TS = datetime.now().isoformat()


async def view_get_healthcheck(request: Request):
    """ Healthcheck endpoint (required for AWS) """
    return json_200({'status': 'ok', 'ts': TS})
