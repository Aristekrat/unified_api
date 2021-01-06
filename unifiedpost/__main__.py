from argparse import ArgumentParser
from pathlib import Path
from typing import Dict, Any

import aiohttp.web
import yaml

from .app import create_app
from .log import setup_logging
from .settings import ENVS, ENV_PROD


def main():
    """
    Application entry-point.
    Parse args, setup logging, create an app instance and runs the web server
    """
    args = parse_args()
    config = load_config(args.env)
    debug = args.env != ENV_PROD
    setup_logging(debug=debug)
    app = create_app(config=config, debug=debug)
    aiohttp.web.run_app(app, port=args.port)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--port', default=8080, help='Application TCP port')
    parser.add_argument('--env', required=True, choices=ENVS, help='Application environment')
    return parser.parse_args()


def load_config(env: str) -> Dict[Any, Any]:
    """
    Read and load YAML config based on provided env
    """
    config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'

    with config_path.open('r') as f:
        config = yaml.load(f.read(), Loader=yaml.FullLoader)

    if env not in config:
        raise RuntimeError(f'Cant load configuration section for environment "{env}"')

    return config.pop(env)


if __name__ == '__main__':
    main()
