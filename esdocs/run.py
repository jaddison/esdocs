if __name__ == '__main__':
    import os, sys

    if os.getcwd() not in sys.path:
        # Make sure that `django.setup()` below can find contents of the current
        # directory, so it can find the settings file (it is assumed that the esdocs-django
        # command will be run from the same dir a Django project's manage.py).
        sys.path.append(os.getcwd())

    from .utils import run
    run()
