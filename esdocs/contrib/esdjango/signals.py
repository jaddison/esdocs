import django.dispatch


post_index_created = django.dispatch.Signal(providing_args=["name", "alias", "index", "alias_set"])
post_index_rebuilt = django.dispatch.Signal(providing_args=["name", "alias", "index", "alias_set"])
