from django.apps import AppConfig


class ESDocsConfig(AppConfig):
    name = 'esdocs.contrib.esdjango'

    def ready(self):
        from django.conf import settings
        from ...serializer import Serializer
        from ...utils import register_serializers
        from .settings import (
            ESDOCS_SERIALIZER_MODULES,
            ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS
        )

        from elasticsearch_dsl import connections
        # TODO: perhaps have some more elaborate multi-client creation steps here, based on settings?
        # then, we can pass in the 'default' client into `register_serializers`
        client = connections.create_connection(hosts=settings.ELASTICSEARCH_SERVER, timeout=20)

        # this loads the serializers and initializes compatibility hooks
        register_serializers(ESDOCS_SERIALIZER_MODULES, client=client)
        Serializer.register_hooks(ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS)
