import functools
from typing import Callable, Coroutine

from gi.repository import Gio


def background_task(f: Callable[..., Coroutine]):
    """
    Wraps an async function to be run using ``Gio.Application.create_asyncio_task``.

    Useful to use async functions like signal handlers or GTK template callbacks.

    Note: The return value will be lost, so this is not suitable when you need to
    return something from the coroutine, what might be needed in some signal handlers.
    """

    @functools.wraps(f)
    def decor(*args, **kwargs):
        app = Gio.Application.get_default()
        app.create_asyncio_task(f(*args, **kwargs))  # type: ignore

    return decor
