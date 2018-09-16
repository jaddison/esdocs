from django.conf import settings

ESDOCS_SERIALIZER_MODULES = getattr(settings, 'ESDOCS_SERIALIZER_MODULES', [])
ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS = getattr(settings, 'ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS', []) or [
    'esdocs.contrib.esdjango.compatibility.manager',
    'esdocs.contrib.esdjango.compatibility.geosgeometry',
    'esdocs.contrib.postgresql.compatibility.range_field'
]
