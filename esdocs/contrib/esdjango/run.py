import logging

import django
from django.db import connections

from ...controller import Controller
from ...utils import run as base_run
from .signals import post_index_created, post_index_rebuilt

logger = logging.getLogger(__name__)


class DjangoController(Controller):
    def on_index_created(self, name, alias, index, alias_set):
        post_index_created.send(None, name=name, alias=alias, index=index, alias_set=alias_set)

    def on_index_rebuilt(self, name, alias, index, alias_set):
        post_index_rebuilt.send(None, name=name, alias=alias, index=index, alias_set=alias_set)

    def parallel_prep(self):
        # this method is only used when doing parallel bulk indexing
        # via multiprocessing.Pool (see policies.py)

        # Django connections need to be closed when a new process is
        # forked (will be auto re-opened)
        connections.close_all()

        super().parallel_prep()


def run():
    import os, sys
    if os.getcwd() not in sys.path:
        # Make sure that `django.setup()` below can find contents of the current
        # directory, so it can find the settings file (it is assumed that the esdocs-django
        # command will be run from the same dir a Django project's manage.py).
        sys.path.append(os.getcwd())

    try:
        # Note: the serializers and compatibility hooks are already initialized
        # in esdocs.contrib.esdjango.apps
        django.setup()
    except ImportError:
        logger.info("esdocs-django must be run from the root of your Django project (where manage.py lives).")
        return

    base_run(DjangoController)


if __name__ == '__main__':
    run()