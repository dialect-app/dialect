# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import json
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
    def new():
        """Create a new instance of Session."""
        s_session = Soup.Session()
        s_session.__class__ = Session
        return s_session

    @staticmethod
    def get():
        """Return an active instance of Session."""
        if Session.instance is None:
            Session.instance = Session.new()
        return Session.instance

    @staticmethod
    def get_response(session, result, fail_if_empty=True, raw=False):
        try:
            response = session.send_and_read_finish(result)

            data = Session.read_response(response, fail_if_empty, raw)

            return data
        except GLib.GError as exc:
            raise ResponseError(exc.message) from exc

    @staticmethod
    def read_response(response, fail_if_empty=True, raw=False):
        if raw:
            return response.get_data()

        data = {}
        try:
            data = json.loads(
                response.get_data()
            ) if response else {}
        except Exception as exc:
            logging.warning(exc)

        if not data and fail_if_empty:
            raise ResponseEmpty()

        return data

    @staticmethod
    def encode_data(data):
        data_glib_bytes = None
        try:
            data_bytes = json.dumps(data).encode('utf-8')
            data_glib_bytes = GLib.Bytes.new(data_bytes)
        except Exception as exc:
            logging.warning(exc)
        return data_glib_bytes

    @staticmethod
    def create_message(method, url, data={}, headers={}, form=False):
        if form and data:
            form_data = Soup.form_encode_hash(data)
            message = Soup.Message.new_from_encoded_form(method, url, form_data)
        else:
            message = Soup.Message.new(method, url)
        if data and not form:
            data = Session.encode_data(data)
            message.set_request_body_from_bytes('application/json', data)
        if headers:
            for name, value in headers.items():
                message.get_request_headers().append(name, value)
        if 'User-Agent' not in headers:
            message.get_request_headers().append('User-Agent', 'Dialect App')
        return message

    def multiple(self, messages, callback=None):
        """Keep track of multiple async operations."""
        def on_task_response(session, result, message_callback):
            messages.pop()
            message_callback(session, result)

            # If all tasks are done, run main callback
            if callback is not None and len(messages) == 0:
                callback()

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


class ResponseEmpty(Exception):
    """Exception raised when response is empty."""

    def __init__(self, message='Response is empty'):
        self.message = message
        super().__init__(self.message)
