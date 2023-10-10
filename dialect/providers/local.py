# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
from typing import Callable

from dialect.providers.base import BaseProvider


class LocalProvider(BaseProvider):
    """Base class for providers needing local threaded helpers"""

    def launch_thread(self, worker: Callable, *args):
        """
        Launches a thread using Python's threading.

        Args:
            worker: Function to execute on the thread
            *args: Args for the worker
        """
        threading.Thread(target=worker, args=args, daemon=True).start()
