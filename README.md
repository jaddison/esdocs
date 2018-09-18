This is a modern replacement of [django-simple-elasticsearch](https://github.com/jaddison/django-simple-elasticsearch/) (DSE). Both Django
and Elasticsearch have seen major changes over the years; this is a move to keep up.

##### Why not just update django-simple-elasticsearch?

* DSE is Django-specific; I wanted to build a solution that could be used in a broader scope of applications
* To start fresh and avoid assumptions made in the DSE project
* Dropped support for Python 2

##### Details

* Flexible and modular; eg. Django support is available via a 'contrib' module
* Supports multi-process indexing and asynchronous IO via `gevent`
* Depends on elasticsearch-dsl-py rather than the low level elasticsearch-py package
  * You get a lot of functionality for free!
* Python 3 only

##### Installation

```
pip install esdocs
```

If multi-process indexing is desired, you will want to install it along with the necessary `gevent` dependencies:

```
pip install esdocs[gevent]
```

##### Command Line Usage

```
$ esdocs -h
usage: esdocs [-h] [-v] [--version] [--no_input] [--indexes INDEXES]
              [--using USING] [--multi [MULTI]]
              {list,init,update,rebuild,cleanup} ...

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  --version             show program's version number and exit
  --no_input, --noinput
                        Do not prompt for user input (assumes 'Yes' for
                        actions)
  --indexes INDEXES     Comma-separate list of index names to target
  --using USING         Elasticsearch named connection to use
  --multi [MULTI]       Enable multiple processes and optionally set number of
                        CPU cores to use (defaults to all cores)

commands:
  {list,init,update,rebuild,cleanup}
    list                List indexes
    init                Initialize indexes
    update              Update indexes
    rebuild             Rebuild indexes
    cleanup             Delete unaliased indexes
```

To rebuild indexes specified by document serializers in `ESDOCS_SERIALIZER_MODULES`:

```
export ESDOCS_SERIALIZER_MODULES="mypackage.module1,myotherpackage.module2"
export ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS="esdocs.contrib.postgresql.compatibility.range_field"

esdocs rebuild
```

Multi-process indexing:
```
export ESDOCS_GEVENT=y
export ESDOCS_SERIALIZER_MODULES="mypackage.module1,myotherpackage.module2"
export ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS="esdocs.contrib.postgresql.compatibility.range_field"

# auto detect number of CPU cores to use
esdocs rebuild --multiproc

# specify the number of cores to use
esdocs rebuild --multiproc --numprocs=4
```

###### Django

You must specify `ESDOCS_SERIALIZER_MODULES` in your Django settings and add `esdocs.contrib.esdjango` to your
`INSTALLED_APPS`. You can optionally set `ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS` as well:

```

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    ...,
    'esdocs.contrib.esdjango'
]


ESDOCS_SERIALIZER_MODULES = [
    'mypackage.module1',
    'myotherpackage.module2'
]

# these are the current defaults for this setting
ESDOCS_SERIALIZER_COMPATIBILITY_HOOKS = [
    'esdocs.contrib.esdjango.compatibility.manager',
    'esdocs.contrib.esdjango.compatibility.geosgeometry',
    'esdocs.contrib.postgresql.compatibility.range_field'
]
```

##### Serializing Data

For esdocs to work, you need to define `Document` and `Serializer` (or `DjangoSerializer`) subclasses to index
your data. `Document` comes from the excellent elasticsearch-dsl-py, while `Serializer`/`DjangoSerializer` are
a part of esdocs.

* `Document` defines the Elasticsearch field mappings
* `Serializer` is associated with a `Document`
* `Serializer` defines how to retrieve the dataset
* For each record in your dataset, the `Serializer` will attempt to retrieve a value for each field defined on the associated `Document`
  * There are a number of methods you can implement on a `Serializer` to retrieve (or construct/munge) each value

###### Examples

```

```