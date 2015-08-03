"""
License for this file:

Copyright (c) 2011 Mateusz Kobos

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
from contextlib import contextmanager
import threading

__author__ = "Mateusz Kobos"


class RWLock:
    """
    Synchronization object used in a solution of so-called second
    readers-writers problem. In this problem, many readers can simultaneously
    access a share, and a writer has an exclusive access to this share.

    Additionally, the following constraints should be met:

    1) no reader should be kept waiting if the share is currently opened for
       reading unless a writer is also waiting for the share,
    2) no writer should be kept waiting for the share longer than absolutely
       necessary.

    The implementation is based on [1]_
    with a modification -- adding an additional lock (:attr:`__readers_queue`)
    -- in accordance with [2]_.

    .. rubric:: Footnotes

    .. [1] A.B. Downey: "The little book of semaphores", Version 2.1.5, 2008,
           See sections 4.2.2, 4.2.6, 4.2.7
    .. [2] P.J. Courtois, F. Heymans, D.L. Parnas:
           "Concurrent Control with 'Readers' and 'Writers'",
           Communications of the ACM, 1971 (via [3]_)
    .. [3] http://en.wikipedia.org/wiki/Readers-writers_problem

    :type __read_switch: _LightSwitch
    :type __write_switch: _LightSwitch
    :type __no_readers: threading.Lock
    :type __no_writers: threading.Lock
    :type __readers_queue: threading.Lock
    """

    def __init__(self):
        self.__read_switch = _LightSwitch()
        self.__write_switch = _LightSwitch()
        self.__no_readers = threading.Lock()
        self.__no_writers = threading.Lock()
        self.__readers_queue = threading.Lock()
        """A lock giving an even higher priority to the writer in certain
        cases (see [2] for a discussion)"""

    @property
    def readers(self) -> int:
        """
        The number of active readers holding this lock

        :return: The number of readers
        """
        return self.__read_switch.counter

    @property
    def writers(self):
        """
        The number of writers holding this lock. May be more than one if there is a queue.

        :return: The number of readers
        """
        return self.__write_switch.counter

    @property
    def blocked_for_readers(self):
        """
        Whether this lock is blocked for readers

        :return: Whether a reader would block when trying to acquire this lock
        """
        have_locked = self.__no_readers.acquire(blocking=False)
        if have_locked:
            # It wasn't locked and we locked it. Let go immediately
            self.__no_readers.release()
        return not have_locked

    @property
    def blocked_for_writers(self):
        """
        Whether this lock is blocked for writers

        :return: Whether a writer would block when trying to acquire this lock
        """
        have_locked = self.__no_writers.acquire(blocking=False)
        if have_locked:
            # It wasn't locked and we locked it. Let go immediately
            self.__no_writers.release()
        return not have_locked

    def reader_acquire(self):
        """
        Acquire the lock as a reader.
        """
        self.__readers_queue.acquire()
        self.__no_readers.acquire()
        self.__read_switch.acquire(self.__no_writers)
        self.__no_readers.release()
        self.__readers_queue.release()

    def reader_release(self):
        """
        Release the reader lock. Must have been acquired first.
        """
        self.__read_switch.release(self.__no_writers)

    def writer_acquire(self):
        """
        Acquire the lock as a writer.
        """
        self.__write_switch.acquire(self.__no_readers)
        self.__no_writers.acquire()

    def writer_release(self):
        """
        Release the writer lock. Must have been acquired first.
        """
        self.__no_writers.release()
        self.__write_switch.release(self.__no_readers)

    @contextmanager
    def read_lock(self):
        """
        A context-manager that acquires a reader lock while in-context.
        """
        self.reader_acquire()
        yield
        self.reader_release()

    @contextmanager
    def write_lock(self):
        """
        A context-manager that acquires a writer lock while in-context.
        """
        self.writer_acquire()
        yield
        self.writer_release()


class _LightSwitch:
    """
    An auxiliary "light switch"-like object. The first thread turns on the
    "switch", the last one turns it off (see [1, sec. 4.2.2] for details).

    :type __counter: int
    :type __mutex: threading.Lock
    """

    def __init__(self):
        self.__counter = 0
        self.__mutex = threading.Lock()

    @property
    def counter(self):
        """
        The number of 'people in the room'. First person entering will turn on the 'switch' (Lock) and the last person
        leaving will turn of the switch/Lock.

        :return: The number of users of this light switch
        """
        return self.__counter

    def acquire(self, lock):
        """
        'Enter the room' equivalent. If this is the first person entering then 'switch the light on' (Lock the lock)

        :param lock: The lock to lock
        """
        self.__mutex.acquire()
        self.__counter += 1
        if self.__counter == 1:
            lock.acquire()
        self.__mutex.release()

    def release(self, lock):
        """
        'Leave the room' equivalent. If this is the last person leaving then 'switch the light off' (Unlock the lock)

        :param lock: The lock to lock
        """
        self.__mutex.acquire()
        self.__counter -= 1
        if self.__counter == 0:
            lock.release()
        self.__mutex.release()
