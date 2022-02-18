# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
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
        s_session.set_user_agent('Dialect App')
        return s_session

    @staticmethod
    def get():
        """Return an active instance of Session."""
        if Session.instance is None:
            Session.instance = Session.new()
        return Session.instance

    @staticmethod
    def get_response(session, result, empty_is_error=True):
        try:
            response = session.send_and_read_finish(result)
            data = Session.read_response(response)

            if data and 'error' in data:
                raise ResponseError(data.get('error'))
            if not data and empty_is_error:
                raise ResponseError('Response is empty')

            return data
        except GLib.GError as exc:
            raise ResponseError(exc.message) from exc

    @staticmethod
    def read_response(response):
        response_data = {}
        try:
            response_data = json.loads(
                response.get_data()
            ) if response else {}
        except Exception as exc:
            logging.warning(exc)
        return response_data

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
    def create_post_message(url, data, headers={}):
        message = Soup.Message.new('POST', url)
        data = Session.encode_data(data)
        message.set_request_body_from_bytes('application/json', data)
        for name, value in headers.items():
            message.request_headers.append(name, value)
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
