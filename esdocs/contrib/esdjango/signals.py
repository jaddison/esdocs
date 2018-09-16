import django.dispatch


post_indexes_create = django.dispatch.Signal(providing_args=["indexes", "aliases_set"])
post_indexes_rebuild = django.dispatch.Signal(providing_args=["indexes", "aliases_set"])
