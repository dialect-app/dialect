import asyncio
import contextlib
from typing import Coroutine

from gi.events import GLibEventLoopPolicy
from gi.repository import GLib


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
    """Create and track a task.
    Normally tasks are weak-referenced by asyncio.
    We keep track of them, so they can be completed
    before GC kicks in.
    """
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task
