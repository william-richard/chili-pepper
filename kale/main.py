import argparse
import importlib
import os
import sys
try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

from typing import Optional

from kale.app import Kale
from kale.deployer import Deployer


class CLI:
    def _load_app(self, app_string, app_dir=None):
        # type: (str, Optional[str]) -> Kale
        # make the app's module is in the path, so it can be imported
        if app_dir is not None:
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)
        else:
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)

        module_name, app_variable = app_string.rsplit('.')
        app = getattr(importlib.import_module(module_name), app_variable)
        return app

    def deploy(self, args):
        # type: (argparse.Namespace) -> None

        app = self._load_app(args.app, args.app_dir)
        deployer = Deployer(app)

        destination_dir = Path(os.getcwd())

        deployer.deploy(dest=destination_dir, app_dir=args.app_dir)


def main():
    cli = CLI()

    parser = argparse.ArgumentParser(description='Serverless asynchronous tasks')
    parser.add_argument('--app', '-A', type=str, help='The Kale application location')

    subparsers = parser.add_subparsers(help='Kale commands')

    deploy_parser = subparsers.add_parser('deploy', help='Deploy functions to serverless provider')
    deploy_parser.set_defaults(func=cli.deploy)
    # TODO implement dry run
    # deploy_parser.add_argument('--dry-run', '-n', action='store_true',
    # help=('Display what would occur if a deploy was executed, without taking remote action'
    #       '(this flag will still create the deploy bundle)'))
    deploy_parser.add_argument('--app-dir',
                               '-d',
                               type=str,
                               required=True,
                               help='The directory holding all the code that needs to be included in the serverless function bundle')
    # TODO add a deploy destination argument?

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
