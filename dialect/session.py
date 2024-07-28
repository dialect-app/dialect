# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from gi.repository import Gio, GLib, Soup


class Session(Soup.Session):
    """
    Dialect soup session handler
    """

    instance = None
    errors = {}

    def __init__(self, *args):
        super().__init__(*args)

    @staticmethod
    def new() -> Session:
        """Create a new instance of Session."""
        s_session = Session()
        return s_session

    @staticmethod
    def get() -> Session:
        """Return an active instance of Session."""
        if Session.instance is None:
            Session.instance = Session.new()
        return Session.instance

    @staticmethod
    def get_response(session: Session, result: Gio.AsyncResult):
        try:
            response = session.send_and_read_finish(result)
            data = response.get_data()

            return data
        except GLib.Error as exc:
            raise ResponseError(exc.message) from exc


class ResponseError(Exception):
    """Exception raised when response fails."""

    def __init__(self, cause: str, message="Response has failed"):
        self.cause = cause
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}: {self.cause}"
