from django.db.models.manager import BaseManager
from django.contrib.gis.geos import GEOSGeometry


def manager(value):
    if isinstance(value, BaseManager):
        return value.all()
    return value


def geosgeometry(value):
    if isinstance(value, GEOSGeometry):
        return list(value)
    return value
