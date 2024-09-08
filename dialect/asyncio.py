import asyncio
import contextlib
import functools
from typing import Callable, Coroutine

from gi.events import GLibEventLoopPolicy


@contextlib.contextmanager
def glib_event_loop_policy():
    original = asyncio.get_event_loop_policy()
    policy = GLibEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    try:
        yield policy
    finally:
        asyncio.set_event_loop_policy(original)


_background_tasks: set[asyncio.Task] = set()


def create_background_task(coro: Coroutine) -> asyncio.Task:
    """
    Create and track a task.

    Normally tasks are weak-referenced by asyncio.
    We keep track of them, so they can be completed before GC kicks in.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


def background_task(f: Callable[..., Coroutine]):
    """
    Wraps an async function to be run using ``create_background_task``.

    Useful to use async functions like signal handlers or GTK template callbacks.

    Note: The return value will be lost, so this is not suitable when you need to
    return something from the coroutine, what might be needed in some signal handlers.
    """

    @functools.wraps(f)
    def decor(*args, **kwargs):
        create_background_task(f(*args, **kwargs))

    return decor
