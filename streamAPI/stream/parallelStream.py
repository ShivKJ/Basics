from collections import deque
from concurrent.futures import (Executor, Future, ProcessPoolExecutor,
                                ThreadPoolExecutor, as_completed)
from functools import partial
from operator import itemgetter
from typing import Deque, Iterable

from decorator import decorator

from streamAPI.stream.decos import cancel_remaining_jobs, check_stream
from streamAPI.stream.stream import Stream
from streamAPI.utility.Types import (Consumer, Filter, Function, T,
                                     X)
from streamAPI.utility.utils import get_functions_clazz


@decorator
def _use_exec(func, *args, **kwargs):
    self: 'ParallelStream' = args[0]
    processing_func = args[1]

    if kwargs['use_exec'] and self._exec is not None:
        self._pointer = self._func_wrapper(processing_func, kwargs.get('single_chunk', False))
        processing_func = Future.result

    return getattr(Stream, func.__name__)(self, processing_func)


class ParallelStream(Stream[T]):
    def __init__(self, data: Iterable[T]):
        super().__init__(data)

        self._concurrent_worker: Deque[Future] = deque()
        self._exec: Executor = None
        self._worker: int = None

    def concurrent(self, worker: int, is_parallel: bool) -> 'ParallelStream[T]':
        """
        This method is called before any method must evoke concurrency.

        :param worker: number of workers
        :param is_parallel: if True then uses Parallel processing otherwise MultiThreading
        :return:
        """
        if self._exec is not None:
            raise AttributeError('Executor was initialized before.')

        self._worker = worker
        self._exec = ProcessPoolExecutor if is_parallel else ThreadPoolExecutor
        self._exec = self._exec(max_workers=worker)

        return self

    def _func_wrapper(self: 'ParallelStream[T]', func, single_chunk=False) -> Stream[T]:
        """
        provides a wrapper around given function.
        :param self:
        :param func:
        :param single_chunk: if False, the run jobs in chunks defined as self._worker else all
                jobs are submitted.
        :return:
        """

        stream = (Stream(self)
                  .map(partial(self._submit_job, func))
                  .peek(self._concurrent_worker.append))

        if single_chunk is False:  # batch processing
            stream = (stream
                      .batch(self._worker)
                      .map(as_completed)
                      .flat_map())

        return stream

    @_use_exec
    def map(self, func: Function[T, X], *, use_exec=True) -> 'ParallelStream[X]':
        pass

    def _submit_job(self, func, g) -> Future:
        return self._exec.submit(func, g)

    @check_stream
    def filter(self, predicate: Filter[T], *, use_exec=True) -> 'ParallelStream[T]':

        if use_exec and self._exec is not None:
            def _predicate(g):
                return predicate(g), g

            self._pointer = (self._func_wrapper(_predicate, single_chunk=False)
                             .map(Future.result)
                             .filter(itemgetter(0))
                             .map(itemgetter(1)))
        else:
            self._pointer = filter(predicate, self._pointer)

        return self

    # terminal operation will trigger cancelling of submitted unnecessary jobs.
    partition = cancel_remaining_jobs(Stream.partition)
    count = cancel_remaining_jobs(Stream.count)
    min = cancel_remaining_jobs(Stream.min)
    max = cancel_remaining_jobs(Stream.max)
    group_by = cancel_remaining_jobs(Stream.group_by)
    mapping = cancel_remaining_jobs(Stream.mapping)
    as_seq = cancel_remaining_jobs(Stream.as_seq)
    all = cancel_remaining_jobs(Stream.all)
    any = cancel_remaining_jobs(Stream.any)
    none_match = cancel_remaining_jobs(Stream.none_match)
    find_first = cancel_remaining_jobs(Stream.find_first)
    reduce = cancel_remaining_jobs(Stream.reduce)
    __iter__ = cancel_remaining_jobs(Stream.__iter__)

    @cancel_remaining_jobs
    @_use_exec
    def for_each(self, consumer: Consumer[T], *, use_exec=True, single_chunk=True):
        pass


if __name__ == 'streamAPI.stream.parallelStream':
    __all__ = get_functions_clazz(__name__, __file__)
