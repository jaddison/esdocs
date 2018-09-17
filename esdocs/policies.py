from multiprocessing import current_process
import os

from elasticsearch_dsl import connections
import gevent
from gevent.pool import Pool
from gevent.queue import Queue
from gevent.select import select
import gipc

from .serializer import Serializer


class BaseIndexingPolicy:
    def bulk_operation(self, serializer, index, client, **options):
        raise NotImplementedError

    def close(self):
        pass


class StreamingPolicy(BaseIndexingPolicy):
    def bulk_operation(self, serializer, index, client, **options):
        serializer.bulk_operation(index=index, client=client, **options)


def process_func(h2):
    proc = current_process()

    def parallel_bulk_index(serializer_hash, index, options):
        serializer = Serializer.hash_registry[serializer_hash]

        using = options.get('using', '') or None
        client = connections.get_connection(using or 'default')

        serializer.bulk_operation(index=index, client=client, **options)

    h2.put(['GOOD-MORNING-DAVE', (proc.name, )])

    queue = Queue()

    def chunk_params_receiver():
        while True:
            args = h2.get()
            queue.put_nowait(args)
            if args == 'STOP':
                break

    gevent.spawn(chunk_params_receiver)

    # Use a gevent pool to maximize processor usage; while a DB query is
    # running, the other green thread can be CPU bound. Then that CPU-heavy
    # task is done, the DB query will likely be completed and ready to
    # become CPU bound (serializing the data)
    pool = Pool(2)
    n = 0
    while True:
        args = queue.get()
        if args == 'STOP':
            break
        chunk_num = args[2]['parallel_chunk_num']
        thread_name = "gthread-{}".format(n)
        pool.apply_async(parallel_bulk_index, args=args, callback=lambda x: h2.put(['DONE-CHUNK', (proc.name, thread_name, chunk_num)]))
        n += 1

    pool.join()


class ParallelStreamingPolicy(BaseIndexingPolicy):
    pipe_fd_mapping = {}

    def __init__(self, parallel_prep):
        self.parallel_prep = parallel_prep

    def bulk_operation(self, serializer, index, client, **options):
        procs = options.get('multi')
        if not procs:
            procs = os.cpu_count()
            procs = procs if procs > 1 else 2

        data_size = serializer.fetch_data_length()
        chunk_size = int(data_size / (procs * 4))

        def parallel_params():
            for chunk_num in range(procs * 4 + 1):
                _options = options.copy()
                _options['parallel_chunk_num'] = chunk_num
                _options['parallel_chunk_size'] = chunk_size
                yield hash(serializer), index, _options

        if not self.pipe_fd_mapping:
            # reset multiprocessing.Process-sensitive elements just before forking
            self.parallel_prep()
            for n in range(procs):
                h1, h2 = gipc.pipe(duplex=True)
                self.pipe_fd_mapping[h1._reader._fd] = (
                    h1, gipc.start_process(process_func, args=(h2,), name="esdocs-proc-{}".format(n))
                )

            # wait until sub-process workers check in
            ready = 0
            while ready != procs:
                readable, _, _ = select(self.pipe_fd_mapping.keys(), [], [])
                for fd in readable:
                    h1, proc = self.pipe_fd_mapping[fd]
                    msg, data = h1.get()
                    if msg == 'GOOD-MORNING-DAVE':
                        ready += 1

        parallel_chunk_params = parallel_params()

        # populate all the processes with an even number of chunks to process
        chunks_remaining = True
        chunks_to_process = 0
        while chunks_remaining:
            for h1, proc in self.pipe_fd_mapping.values():
                try:
                    h1.put(next(parallel_chunk_params))
                    chunks_to_process += 1
                except StopIteration:
                    chunks_remaining = False
                    break

        while chunks_to_process > 0:
            readable, _, _ = select(self.pipe_fd_mapping.keys(), [], [])
            for fd in readable:
                h1, proc = self.pipe_fd_mapping[fd]
                msg, data = h1.get()
                if msg == 'DONE-CHUNK':
                    chunks_to_process -= 1

    def close(self):
        for h1, proc in self.pipe_fd_mapping.values():
            h1.put('STOP')
        for h1, proc in self.pipe_fd_mapping.values():
            proc.join()
