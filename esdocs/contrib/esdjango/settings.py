from django.conf import settings

ESDOCS_USING = getattr(settings, 'ESDOCS_USING', None) or 'default'
ESDOCS_CONNECTIONS = getattr(settings, 'ESDOCS_CONNECTIONS', {}) or {
    'default': 'localhost:9200'
}

ESDOCS_SERIALIZER_MODULES = getattr(settings, 'ESDOCS_SERIALIZER_MODULES', [])
ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS = getattr(settings, 'ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS', []) or [
    'esdocs.contrib.esdjango.compatibility.manager',
    'esdocs.contrib.esdjango.compatibility.geosgeometry',
    'esdocs.contrib.postgresql.compatibility.range_field'
]
