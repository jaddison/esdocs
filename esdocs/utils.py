import argparse
import logging
import os

from . import gevent_enabled
from .controller import Controller
from .serializer import Serializer

logger = logging.getLogger(__name__)


def register_serializers(modules, client=None):
    if modules is not None:
        if isinstance(modules, str):
            modules = [s.strip() for s in modules.split(',')]

        if modules:
            for mod in modules:
                logger.debug("Looking for serializers in '{}'...".format(mod))
                # a simple import triggers metaclass Serializer class 'self-registration'
                __import__(mod)
            Serializer.client = client
        else:
            logger.warning('No serializer modules specified!')


def add_parser_arguments(parser):
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('--no_input', '--noinput', action='store_true', default=False,
                        help="Do not prompt for user input (assumes 'Yes' for actions)")
    parent.add_argument('--indexes', action='store', default='',
                        help="Comma-separate list of index names to target")
    parent.add_argument('--using', action='store', default=None,
                        help="Elasticsearch named connection to use")
    parent.add_argument('--multi', nargs='?', const=0, type=int,
                        help="Enable multiple processes and optionally set number of "
                             "CPU cores to use (defaults to all cores)")

    # hack to get comment args into the main parser;
    # stolen from python argparse source code
    parser._add_container_actions(parent)
    try:
        defaults = parent._defaults
    except AttributeError:
        pass
    else:
        parser._defaults.update(defaults)

    sps = parser.add_subparsers(title="commands", dest='action')
    # this is a hack for a Django 1.11 bug:
    # https://code.djangoproject.com/ticket/29295;
    # TODO: remove when we drop support for broken Django versions
    sps._parser_class = argparse.ArgumentParser

    p = sps.add_parser('list', help="List indexes", parents=[parent])
    p = sps.add_parser('init', help="Initialize indexes", parents=[parent])
    p = sps.add_parser('update', help="Update indexes", parents=[parent])
    p = sps.add_parser('rebuild', help="Rebuild indexes", parents=[parent])
    p.add_argument('--cleanup', action="store_true", dest='delete_old_indexes',
                   default=False)
    p = sps.add_parser('cleanup', help="Delete unaliased indexes", parents=[parent])


def run(controller_klass=None):
    import argparse
    import logging

    from . import app_version, logger as parent_logger

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    parser.add_argument("--version", action="version", version=app_version)
    add_parser_arguments(parser)
    args = parser.parse_args()

    if args.verbose:
        logf = logging.Formatter('%(message)s (%(name)s:%(lineno)d)')
        parent_logger.setLevel(logging.DEBUG)
    else:
        logf = logging.Formatter('%(message)s')
        parent_logger.setLevel(logging.INFO)

    logh = logging.StreamHandler()
    logh.setFormatter(logf)

    parent_logger.addHandler(logh)

    logger.info('Logging enabled at {} verbosity'.format(
        logging.getLevelName(logger.getEffectiveLevel())))

    if not gevent_enabled and args.multi is not None:
        logger.error('Multi-process indexing not available unless environment '
                     'variable ESDOCS_GEVENT=1 is set, stopping...')
        return
    else:
        logger.info('Multi-process indexing: {}'.format(
            'available' if gevent_enabled else 'unavailable (set environment '
                                               'variable ESDOCS_GEVENT=1)'))

    register_serializers(os.getenv('ESDOCS_SERIALIZER_MODULES'))
    Serializer.register_hooks(os.getenv('ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS'))

    options = vars(args)
    if not controller_klass:
        controller_klass = Controller
    controller = controller_klass(**options)
    controller.run_operation(cmd_parser=parser, **options)
