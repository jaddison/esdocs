from django.core.paginator import Paginator as DjangoPaginator


class Paginator(DjangoPaginator):
    def __init__(self, response, *args, **kwargs):
        count = kwargs.pop('total_count', None)

        # `response` is a generator (MutableSequence), however `Paginator` was changed in 1.10
        # to require an object with either a `.count()` method (ie. QuerySet) or able
        # to call `len()` on the object - forcing the generator to resolve to a list
        # for this reason.
        super().__init__(response, *args, **kwargs)

        if count is None:
            # Override to set the count/total number of items; Elasticsearch provides the total
            # as a part of the query results, so we can minimize hits.
            self._count = response.hits.total
        else:
            # this allows us to manually set the total count; typically most useful when using
            # a cardinality aggregation to get a count
            self._count = count

    def page(self, number):
        # this is overridden to prevent any slicing of the object_list - Elasticsearch has
        # returned the sliced data already.
        number = self.validate_number(number)
        return self._get_page(self.object_list, number, self)

    @property
    def count(self):
        return self._count
