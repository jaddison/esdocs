from ...serializer import Serializer


class DjangoSerializer(Serializer):
    model = None
    queryset_ordering = 'pk'
    queryset_select_related = []
    queryset_chunk_size = 500

    @classmethod
    def get_queryset(cls, for_count=False, coerce=False):
        if not cls.model:
            raise NotImplementedError("The 'model' attribute is missing.")
        qs = cls.model.objects.all()
        if for_count:
            return qs
        return qs.select_related(*cls.queryset_select_related)

    @classmethod
    def fetch_data_length(cls, **kwargs):
        queryset = kwargs.get('queryset')
        if queryset is None:
            queryset = cls.get_queryset(for_count=True)

        return queryset.count()

    @classmethod
    def fetch_data(cls, **kwargs):
        queryset = kwargs.get('queryset')
        coerce = kwargs.get('coerce', False)
        if queryset is None:
            queryset = cls.get_queryset(for_count=False, coerce=coerce)

        if cls.queryset_ordering:
            queryset = queryset.order_by(cls.queryset_ordering)

        start = 0
        end = None
        if 'parallel_chunk_num' in kwargs:
            parallel_chunk_num = kwargs.get('parallel_chunk_num')
            parallel_chunk_size = kwargs.get('parallel_chunk_size')
            start = parallel_chunk_num * parallel_chunk_size
            end = (parallel_chunk_num + 1) * parallel_chunk_size

        chunk = 0
        while True:
            queryset_start = start + (chunk * cls.queryset_chunk_size)
            queryset_end = start + ((chunk + 1) * cls.queryset_chunk_size)

            # if we're bulk indexing in parallel, make sure we don't go
            # beyond the given process' allocated parallel chunk size
            if end and queryset_end > end:
                queryset_end = end

            n = 0
            for n, row in enumerate(queryset[queryset_start: queryset_end]):
                yield row

            if not n:
                break
            chunk += 1

    @classmethod
    def save_handler(cls, sender, instance, **kwargs):
        cls.index_add_or_delete(instance)

    @classmethod
    def delete_handler(cls, sender, instance, **kwargs):
        cls.index_delete(instance)
