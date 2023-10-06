# Copyright 2022 Mufeed Ali
# Copyright 2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
from typing import Callable

from gi.repository import GLib, Gio, Soup

from dialect.providers.base import BaseProvider, ProviderError, ProviderErrorCode
from dialect.session import Session

class SoupProvider(BaseProvider):
    """Base class for providers needing libsoup helpers"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def encode_data(data) -> GLib.Bytes | None:
        """Convert dict to JSON and bytes"""
        data_glib_bytes = None
        try:
            data_bytes = json.dumps(data).encode('utf-8')
            data_glib_bytes = GLib.Bytes.new(data_bytes)
        except Exception as exc:
            logging.warning(exc)
        return data_glib_bytes

    @staticmethod
    def read_data(data: bytes) -> dict:
        """Get JSON data from bytes"""
        return json.loads(data) if data else {}

    @staticmethod
    def read_response(session: Session, result: Gio.AsyncResult) -> dict:
        """Get JSON data from session result"""
        response = session.get_response(session, result)
        return SoupProvider.read_data(response)

    @staticmethod
    def create_message(method: str, url: str, data={}, headers: dict = {}, form: bool = False) -> Soup.Message:
        """Helper for creating libsoup's message"""

        if form and data:
            form_data = Soup.form_encode_hash(data)
            message = Soup.Message.new_from_encoded_form(method, url, form_data)
        else:
            message = Soup.Message.new(method, url)
        if data and not form:
            data = SoupProvider.encode_data(data)
            message.set_request_body_from_bytes('application/json', data)
        if headers:
            for name, value in headers.items():
                message.get_request_headers().append(name, value)
        if 'User-Agent' not in headers:
            message.get_request_headers().append('User-Agent', 'Dialect App')
        return message

    @staticmethod
    def send_and_read(message: Soup.Message, callback: Callable[[Session, Gio.AsyncResult], None]):
        """Helper method for libsoup's send_and_read_async
        Useful when priority and cancellable is not needed"""
        Session.get().send_and_read_async(message, 0, None, callback)

    @staticmethod
    def check_known_errors(data: dict) -> None | ProviderError:
        """Checks data for possible response errors and return a found error if any
        This should be implemented by subclases"""
        return None

    @staticmethod
    def process_response(
        session: Session,
        result: Gio.AsyncResult,
        on_continue: Callable[[dict], None],
        on_fail: Callable[[ProviderError], None],
        check_common: bool = True,
        json: bool = True
    ):
        """Helper method for the most common workflow for processing soup responses

        Checks for soup errors, then checks for common errors on data and calls on_fail
        if any, otherwise calls on_continue where the provider will finish the process.
        """

        try:
            if json:
                data = SoupProvider.read_response(session, result)

                if check_common:
                    error = SoupProvider.check_known_errors(data)
                    if error:
                        on_fail(error)
                        return
            else:
                data = Session.get_response(session, result)                

            on_continue(data)

        except Exception as exc:
            logging.warning(exc)
            on_fail(ProviderError(ProviderErrorCode.NETWORK, str(exc)))

    @staticmethod
    def send_and_read_and_process_response(
        message: Soup.Message,
        on_continue: Callable[[dict], None],
        on_fail: Callable[[ProviderError], None],
        check_common: bool = True,
        json: bool = True
    ):
        """Helper packaging send_and_read and process_response

        Avoids implementors having to deal with many callbacks."""

        def on_response(session: Session, result: Gio.AsyncResult):
            SoupProvider.process_response(session, result, on_continue, on_fail, check_common, json)

        SoupProvider.send_and_read(message, on_response)
