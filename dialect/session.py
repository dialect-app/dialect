# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging

from gi.repository import GLib, Soup


class Session(Soup.Session):
    """
    Dialect soup session handler
    """

    instance = None

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

        def on_task_response(session, result, message_callback):
            messages.pop()

            try:
                data = Session.get_response(session, result)
                message_callback(data)
            except ResponseError as exc:
                logging.warning(exc)
                if self.errors:
                    self.errors += '/n'
                self.errors += str(exc)

            # If all tasks are done, run main callback
            if callback is not None and len(messages) == 0:
                callback(errors=self.errors)

        self.errors = ''  # FIXME: We're assuming that multiple() isn't called twice simultaneously

        for msg in messages:
            # msg[0]: Soup.Message
            # msg[1]: message callback
            self.send_and_read_async(msg[0], 0, None, on_task_response, msg[1])


class ResponseError(Exception):
    """Exception raised when response fails."""

    def __init__(self, cause, message='Response has failed'):
        self.cause = cause
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}: {self.cause}'
