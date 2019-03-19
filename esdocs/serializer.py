import collections
import logging

from elasticsearch.helpers import streaming_bulk

from .exceptions import *

logger = logging.getLogger(__name__)


def dotted_import(path):
    module, klass = path.rsplit('.', 1)
    mod = __import__(module, fromlist=[klass])
    return getattr(mod, klass)


class _SerializerMetaclass(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)

        if not hasattr(cls, 'registry'):
            logger.debug('Initializing serializer registry')
            cls.registry = {}
            cls.hash_registry = {}

        if cls.document and cls.document not in cls.registry:
            # # this will raise if '*' is in the index name (we
            # # don't want wildcard indexes)
            # try:
            #     if '*' in cls.document._default_index():
            #         return
            # except AttributeError:
            #     # InnerDocs don't have `_default_index()`
            #     return
            logger.debug('Registering {} serializer for {}'.format(name, cls.document))
            cls.registry[cls.document] = cls
            cls.hash_registry[hash(cls)] = cls


class Serializer(metaclass=_SerializerMetaclass):
    compatibility_hooks = set()
    document = None
    index = None
    map_fields = {}
    data_bulk_limit = 500
    parallel_count = None
    client = None

    @classmethod
    def register_hooks(cls, modules):
        if modules is not None:
            if isinstance(modules, str):
                modules = [s.strip() for s in modules.split(',')]

            if modules:
                logger.debug('Adding serializer compatibility hooks...')
                for mod in modules:
                    logger.debug('Added {}'.format(mod))
                    Serializer.compatibility_hooks.add(dotted_import(mod))
            else:
                logger.debug('No serializer compatibility hooks specified.')

    @classmethod
    def normalize_value(cls, value):
        # override this in derivative apps like esdocs.contrib.django
        # to ensure QuerySets are returned properly (instead of Managers, etc)
        # Postgres Ranges, etc
        # BUT consider using compatibility hooks instead
        if isinstance(value, str):
            return value.strip()
        return value

    @classmethod
    def adjust_value(cls, name, value, source=None):
        # override this to filter/adjust data if necessary
        """ # example:
        if name == 'sessions':
            return value.filter(start__gte=today)
        return value
        """
        return value

    @classmethod
    def get_value(cls, obj, name, source=None):
        parts = (cls.map_fields.get(name) or name).split('.')
        v = obj
        for n, part in enumerate(parts, start=1):
            try:
                v = getattr(v, part)
            except AttributeError:
                if not isinstance(v, collections.Mapping):
                    raise
                v = v.get(part)

            if v is None and n != len(parts):
                # if we have None and we haven't finished processing the
                # dot-separated field lookup, then it will blow up on the
                # next iteration; handle it before it does
                # eg. if a related Django ForeignKey field is set to `None`
                raise InvalidFieldLookup

        return v

    @classmethod
    def serialize(cls, obj, source=None):
        if not hasattr(cls, 'doc_fields'):
            cls.doc_fields = cls.document._doc_type.mapping.properties.properties.to_dict()

        if source is None:
            source = obj

        data = {}
        for name, field in cls.doc_fields.items():
            empty = False
            try:
                # first attempt user-defined method of manual serialization
                v = getattr(cls, 'serialize_{}'.format(name))(obj, source)
            except AttributeError:
                try:
                    # first attempt user-defined method
                    v = getattr(cls, 'get_{}_value'.format(name))(obj, source)
                except AttributeError:
                    try:
                        v = cls.get_value(obj, name, source)
                    except InvalidFieldLookup:
                        v = field.empty()
                        empty = True

                    if callable(v):
                        v = v()

                for f in cls.compatibility_hooks: v = f(v)
                v = cls.normalize_value(v)
                v = cls.adjust_value(name, v)

                if not empty and v is not None:
                    # if the field is an Object or Nested inner doc, the user will have
                    # defined an InnerDoc Mapper; if a related Serializer exists, it will
                    # be used to populate data
                    try:
                        subdoc = getattr(field, '_doc_class')
                    except AttributeError:
                        pass
                    else:
                        try:
                            serializer = cls.registry[subdoc]
                        except KeyError:
                            raise MissingSerializer("Every Document and inner Document must have a registered Serializer.")
                        else:
                            if hasattr(v, '__iter__'):
                                v = [serializer.serialize(_v, source) for _v in v]
                            else:
                                v = serializer.serialize(v, source)

            data[name] = v

        return data

    @classmethod
    def get_meta_value(cls, obj, name):
        try:
            # first attempt user-defined method
            func = getattr(cls, 'get_meta_{}_value'.format(name))
        except AttributeError:
            meta_lookup_value = getattr(cls, 'map_{}'.format(name), None)
            if meta_lookup_value:
                try:
                    v = cls.get_value(obj, meta_lookup_value)
                except InvalidFieldLookup:
                    raise

                if callable(v):
                    v = v()

                return v
        else:
            return func(obj)

    @classmethod
    def should_index(cls, obj, client=None):
        return True

    @classmethod
    def index_add_or_delete(cls, obj, client=None):
        if not cls.index_add(obj, client):
            cls.index_delete(obj, client)

    @classmethod
    def index_add(cls, obj, client=None):
        if cls.should_index(obj, client):
            data = cls.serialize(obj)
            params = {}
            # `id` can be None, causing ES to generate an id for
            # the doc (not desired in the parent of a parent/child
            # join field; it needs to be known to join properly)
            _id = cls.get_meta_value(obj, 'id')
            routing = cls.get_meta_value(obj, 'routing')
            if routing is not None:
                params['routing'] = routing

            (client or cls.client).index(cls.document._default_index(), 'doc', data, id=_id, params=params)
            return True
        return False

    @classmethod
    def index_delete(cls, obj, client=None):
        params = {}
        # `id` can be None, causing ES to generate an id for
        # the doc (not desired in the parent of a parent/child
        # join field; it needs to be known to join properly)
        _id = cls.get_meta_value(obj, 'id')
        routing = cls.get_meta_value(obj, 'routing')
        if routing is not None:
            params['routing'] = routing

        (client or cls.client).delete(cls.document._default_index(), 'doc', id=_id, params=params, ignore=[404])

    @classmethod
    def fetch_data(cls, **kwargs):
        raise NotImplementedError

    @classmethod
    def fetch_data_length(cls, **kwargs):
        raise NotImplementedError

    @classmethod
    def _bulk_stream(cls, op_type=None, **options):
        op_type = op_type if op_type else 'index'
        for o in cls.fetch_data(**options):
            data = {}
            op = op_type
            if op != 'delete':
                if not cls.should_index(o):
                    op = 'delete'
                else:
                    data = cls.serialize(o)

            data['_op_type'] = op

            _id = cls.get_meta_value(o, 'id')
            if _id is not None:
                data['_id'] = _id

            routing = cls.get_meta_value(o, 'routing')
            if routing is not None:
                data['routing'] = routing

            yield data

    @classmethod
    def bulk_operation(cls, index=None, client=None, **options):
        for ok, result in streaming_bulk(
                client or cls.client,
                cls._bulk_stream(**options),
                index=index or cls.document._default_index(),
                doc_type='doc',
                raise_on_error=False,
                yield_ok=False,
                chunk_size=cls.data_bulk_limit
        ):
            if not ok:
                action, result = result.popitem()
                doc_id = '/%s/doc/%s' % (index, result['_id'])
                logger.warning('Failed to {} document {}: {}'.format(action, doc_id, result))
