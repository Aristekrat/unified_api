from argparse import ArgumentParser
import aiohttp.web

from .common import setup_logging
from .settings import ENVS, ENV_PROD
from .app import create_app


def main():
    args = parse_args()
    debug = args.env != ENV_PROD
    setup_logging(debug=debug)
    app = create_app(args=args, debug=debug)
    aiohttp.web.run_app(app, port=args.port)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--port', default=8080)
    parser.add_argument('--env', required=True, choices=ENVS)
    parser.add_argument('--disable-parser', action='store_true')
    return parser.parse_args()


if __name__ == '__main__':
    main()
