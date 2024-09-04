# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import asyncio
import concurrent.futures
from typing import Callable, TypeVar

from dialect.providers.base import BaseProvider


class LocalProvider(BaseProvider):
    """Base class for providers needing local threaded helpers"""

    _T = TypeVar("_T")

    async def run_async(self, worker: Callable[..., _T], *args) -> _T:
        """
        Runs worker in a ThreadPoolExecutor.

        Args:
            worker: Function to execute on the thread
            *args: Args for the worker
        """

        loop = asyncio.get_running_loop()

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, worker, *args)
