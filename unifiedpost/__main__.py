from argparse import ArgumentParser

import aiohttp.web

from .app import create_app
from .log import setup_logging
from .settings import ENVS, ENV_PROD


def main():
    """
    Application entry-point.
    Parse args, setup logging, create an app instance and runs the web server
    """
    args = parse_args()
    debug = args.env != ENV_PROD
    setup_logging(debug=debug)
    app = create_app(args=args, debug=debug)
    aiohttp.web.run_app(app, port=args.port)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--port', default=8080, help='Application TCP port')
    parser.add_argument('--env', required=True, choices=ENVS, help='Application environment')
    return parser.parse_args()


if __name__ == '__main__':
    main()
