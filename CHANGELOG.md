#### 2018-10-03 version 0.4

* Backward incompatible: Modifying the Django signals to include the Index object

#### 2018-10-02 version 0.3

* Fixing connection reset issue when using multi-processing and a remote Elasticsearch server
* Backward incompatible: changed the way Django configures Elasticsearch connection settings

#### 2018-09-26 version 0.2

* Adding in post index create/rebuilt `Controller` hooks and associated Django signals
* Fixed bug related to callable meta values

#### 2018-09-19 version 0.1.4

* Ensured that appropriate default data was serialized for missing fields.

#### 2018-09-18 version 0.1.3

* Doc updates, bug fix (random empty logger.info call).

#### 2018-09-17 version 0.1.2

* Simplified command arguments for multiprocessing
* Moved from print statements to pure Python logging-based output

#### 2018-09-15 version 0.1

* Initial release
