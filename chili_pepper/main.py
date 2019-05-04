import argparse
import importlib
import os
import string
import sys
import logging

try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

try:
    from typing import Optional
except ImportError:
    # python2.7 doesn't have typing, and I don't want to mess with mypy yet
    pass

from chili_pepper.app import ChiliPepper
from chili_pepper.deployer import Deployer


class CLI:
    """Implements the ``chili`` command line interface
    """

    def __init__(self):
        # set up logging
        logger = logging.getLogger("chili_pepper")
        logger.setLevel(logging.INFO)

        if len(logger.handlers) == 0:
            ch = logging.StreamHandler()
            logger.addHandler(ch)

    def _load_app(self, app_string, app_dir=None):
        # type: (str, Optional[str]) -> ChiliPepper
        # make the app's module is in the path, so it can be imported
        if app_dir is not None:
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)
        else:
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)

        try:
            module_name, app_variable = app_string.rsplit(".", maxsplit=1)
        except TypeError:
            # python2.7 doesn't take keyword args for rsplit
            module_name, app_variable = string.rsplit(app_string, ".", 1)
        app_module = importlib.import_module(module_name)
        app = getattr(app_module, app_variable)
        return app

    def deploy(self, args):
        # type: (argparse.Namespace) -> None
        """Deploys a Chili-Pepper app

        Args:
            args (argparse.Namespace): Arguments passed to the command line.
        """

        app = self._load_app(args.app, args.app_dir)
        deployer = Deployer(app)

        deployer.deploy(dest=Path(args.deployment_package_dir), app_dir=Path(args.app_dir))


def main():
    """
    Main Chili-Pepper command line interface handler
    """
    cli = CLI()

    parser = argparse.ArgumentParser(description="Serverless asynchronous tasks")
    parser.add_argument("--app", "-A", type=str, help="The Chili-Pepper application location")
    # TODO add verbose and quiet args

    subparsers = parser.add_subparsers(help="Chili-Pepper commands")

    deploy_parser = subparsers.add_parser("deploy", help="Deploy functions to serverless provider")
    deploy_parser.set_defaults(func=cli.deploy)
    # TODO implement dry run
    # deploy_parser.add_argument('--dry-run', '-n', action='store_true',
    # help=('Display what would occur if a deploy was executed, without taking remote action'
    #       '(this flag will still create the deploy bundle)'))
    deploy_parser.add_argument(
        "--app-dir", type=str, required=True, help="The directory holding all the code that needs to be included in the serverless function bundle"
    )
    deploy_parser.add_argument("--deployment-package-dir", "-d", type=str, default=os.getcwd(), help="The directory to put the deployment package zip")
    # TODO add a deploy destination argument?

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
