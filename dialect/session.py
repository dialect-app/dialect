# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
from uuid import uuid4

from gi.repository import GLib, Soup


class Session(Soup.Session):
    """
    Dialect soup session handler
    """

    instance = None
    errors = {}

    def __init__(self):
        Soup.Session.__init__(self)

    @staticmethod
    def new() -> Session:
        """Create a new instance of Session."""
        s_session = Soup.Session()
        s_session.__class__ = Session
        return s_session

    @staticmethod
    def get() -> Session:
        """Return an active instance of Session."""
        if Session.instance is None:
            Session.instance = Session.new()
        return Session.instance

    @staticmethod
    def get_response(session, result):
        try:
            response = session.send_and_read_finish(result)
            data = response.get_data()

            return data
        except GLib.GError as exc:
            raise ResponseError(exc.message) from exc

    def multiple(self, messages, callback=None):
        """Keep track of multiple async operations."""

        def on_task_response(session, result, message_callback, request_id):
            messages.pop()

            try:
                data = Session.get_response(session, result)
                message_callback(data)
            except ResponseError as exc:
                logging.warning(exc)
                self.errors[request_id] += str(exc) + '/n'

            # If all tasks are done, run main callback
            if callback is not None and len(messages) == 0:
                callback(errors=self.errors[request_id])
                del self.errors[request_id]

        request_id = uuid4()
        self.errors[request_id] = ''

        for msg in messages:
            # msg[0]: Soup.Message
            # msg[1]: message callback
            self.send_and_read_async(msg[0], 0, None, on_task_response, msg[1], request_id)

        return request_id


class ResponseError(Exception):
    """Exception raised when response fails."""

    def __init__(self, cause, message='Response has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.cause}'
