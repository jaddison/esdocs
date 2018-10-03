import datetime
import logging
from collections import defaultdict

import elasticsearch
from elasticsearch_dsl import connections

from .policies import StreamingPolicy, ParallelStreamingPolicy
from .serializer import Serializer

logger = logging.getLogger(__name__)


class Controller:
    _indexes = None
    _new_indexes = None
    _serializers = defaultdict(list)
    client = None

    def __init__(self, **options):
        self.no_input = options.pop('no_input', False)
        self.using = options.get('using', '') or None
        self.client = connections.get_connection(alias=self.using or 'default')

        _indexes = options.pop('indexes', '') or None
        if _indexes:
            _indexes = _indexes.split(',')
        self.index_names = _indexes

    def parallel_prep(self):
        # this is kind of a hack for elasticsearch connections to be
        # 'reset' with their existing settings kept intact
        for label in list(connections.connections._conns.keys()):
            # remove the existing connection (but keeps the _kwargs settings for it
            connections.connections._conns.pop(label, None)
            # recreate the connection using the retained _kwargs (view the source)
            connections.get_connection(label)

    @property
    def indexes(self):
        if self._indexes is None:
            self._indexes = {}
            logger.debug("Discovering indexes from known serializers...")
            for doc, serializer in Serializer.registry.items():
                index = getattr(doc, '_index', None)
                if not index:
                    continue

                self._serializers[index._name].append(serializer)

                if index._name in self._indexes:
                    continue

                if self.index_names is not None and index._name not in self.index_names:
                    logger.debug("Skipping index '{}'".format(index._name))
                    continue

                self._indexes[index._name] = index
                logger.debug("Found index '{}'".format(index._name))

            if not self._indexes:
                logger.debug("No indexes available.")

        return self._indexes

    @property
    def new_indexes(self):
        if self._new_indexes is None:
            self._new_indexes = {}
            date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            for name, i in self.indexes.items():
                new_index = i.clone(name="{}-{}".format(name, date_str))
                self._new_indexes[name] = new_index
        return self._new_indexes

    def run_operation(self, **options):
        action = options.get('action')
        parser = options.pop('cmd_parser', None)
        if parser and not action:
            parser.print_help()
            return

        try:
            getattr(self, "index_{}".format(action))(**options)
        except KeyboardInterrupt:
            pass

    def index_list(self, **options):
        logger.info("Known, managed indexes{}:".format(
            " (limited results due to --indexes option)" if self.index_names else ""))
        for name, index in self.indexes.items():
            logger.info(" - {}".format(name))

    def index_init(self, **options):
        for name, index in self.new_indexes.items():
            if not self.client.indices.exists(name):
                self._index_create(index, name, True)
            else:
                logger.info("Index '{}' already exists. No change made.".format(index._name))

    def index_update(self, **options):
        for name, index in self.indexes.items():
            if not self.client.indices.exists(name):
                self._index_create(self.new_indexes[name], name, True)
            else:
                try:
                    index.save(using=self.using)
                    logger.info("Updated index mapping for '{}'.".format(name))
                except elasticsearch.exceptions.RequestError as e:
                    logger.info(str(e))

    def index_rebuild(self, **options):
        if options.get('multi') is not None:
            policy = ParallelStreamingPolicy(self.parallel_prep)
        else:
            policy = StreamingPolicy()

        for name, index in self.new_indexes.items():
            self._index_create(index, name, set_alias=False)

            logger.info("Updating index settings to be bulk-indexing friendly...")
            original_settings = index.get_settings(using=self.using).get(index._name, {}).get('settings', {})
            index.put_settings(body={
                "index.number_of_replicas": 0,
                "index.refresh_interval": '-1'
            })

            logger.info("Indexing data for '{}'...".format(index._name))

            for serializer in self._serializers[name]:
                logger.info(" - processing '{}' documents".format(serializer.document.__name__))
                policy.bulk_operation(serializer, index=index._name, client=self.client, **options)

            logger.info("Data indexed data for '{}'.".format(index._name))

            logger.info("Force merging index data...")
            index.forcemerge()

            logger.info("Restoring original/default index settings...")
            index.put_settings(body={
                "index.number_of_replicas": original_settings.get('index', {}).get('number_of_replicas', 1),
                "index.refresh_interval": original_settings.get('index', {}).get('refresh_interval', '1s')
            })

            # remove alias from any pre-existing indexes and
            # add it to the one new index
            self.client.indices.update_aliases({
                'actions': [
                    {'remove': {'index': '*', 'alias': name}},
                    {'add': {'index': index._name, 'alias': name}}
                ]
            })
            logger.info("Created alias '{}' for '{}'.".format(name, index._name))

            self.on_index_rebuilt(index._name, name, index, True)

        policy.close()

        self._indexes_delete(**options)

    def index_cleanup(self, **options):
        options['delete_old_indexes'] = True
        self._indexes_delete(**options)

    def on_index_created(self, name, alias, index, alias_set):
        pass

    def on_index_rebuilt(self, name, alias, index, alias_set):
        pass

    def _index_create(self, index, alias, set_alias=False):
        if not set_alias:
            index.create(using=self.using)
            logger.info("Created index '{}', no alias set.".format(index._name))
        else:
            index.aliases(**{alias: {}}).create(using=self.using)
            logger.info("Created index '{}', aliased to '{}'.".format(index._name, alias))

        self.on_index_created(index._name, alias, index, set_alias)

    def _indexes_delete(self, **options):
        old_indexes = []
        for name, index in self.indexes.items():
            _old_indexes = self.client.indices.get_alias("{}-*".format(name))
            # `old_indexes` will contain only those that aren't currently aliased
            old_indexes.extend([_old for _old, data in _old_indexes.items() if not data['aliases']])

        if len(old_indexes) and options.get('delete_old_indexes', False):
            no_input = options.get('no_input', False)
            if no_input:
                self.client.indices.delete(",".join(old_indexes))
                logger.info("Deleting old unaliased indexes:")
                for _old in old_indexes:
                    logger.info(" - deleted index '{}'".format(_old))
            else:
                for _old in old_indexes:
                    user_input = 'y' if no_input else ''
                    while user_input != 'y':
                        user_input = input("Delete index '{}' (y/N) ".format(_old)).lower()
                        if user_input == 'n':
                            break
                    if user_input == 'y':
                        self.client.indices.delete(_old)
                        logger.info(" - deleted index '{}'".format(_old))
