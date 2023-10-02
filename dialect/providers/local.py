# Copyright 2023 Mufeed Ali
# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
from typing import Callable

from dialect.providers.base import BaseProvider


class LocalProvider(BaseProvider):
    """Base class for providers needing local threaded helpers"""

    def launch_thread(self, callback: Callable, *args):
        threading.Thread(target=callback, args=args, daemon=True).start()
