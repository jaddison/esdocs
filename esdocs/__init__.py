import os
use_gevent = str(os.getenv('ESDOCS_GEVENT', 0)).lower() not in ['0', '', 'false', 'f', 'no', 'n']

if use_gevent:
    try:
        from gevent import monkey
        monkey.patch_all()
    except ImportError:
        pass

    try:
        import psycogreen.gevent
        psycogreen.gevent.patch_psycopg()
    except ImportError:
        pass

try:
    import gevent.monkey
    if gevent.monkey.is_module_patched('socket') and gevent.monkey.is_module_patched('os'):
        gevent_enabled = True
    else:
        gevent_enabled = False
except:
    gevent_enabled = False

import logging

__appname__ = __package__
__version__ = "0.5.1"

app_version = "{}/{}".format(__appname__, __version__)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
