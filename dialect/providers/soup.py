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

    def encode_data(self, data) -> GLib.Bytes | None:
        """
        Convert Python data to JSON and bytes.

        Args:
            data: Data to encode, anything json.dumps can handle
        """
        data_glib_bytes = None
        try:
            data_bytes = json.dumps(data).encode('utf-8')
            data_glib_bytes = GLib.Bytes.new(data_bytes)
        except Exception as exc:
            logging.warning(exc)
        return data_glib_bytes

    def create_message(self, method: str, url: str, data={}, headers: dict = {}, form: bool = False) -> Soup.Message:
        """
        Create a libsoup's message.

        Encodes data and adds it to the message as the request body.
        If form is true, data is encoded as application/x-www-form-urlencoded.

        Args:
            method: HTTP method of the message
            url: Url of the message
            data: Request body or form data
            headers: HTTP headers of the message
            form: If the data should be encoded as a form
        """

        if form and data:
            form_data = Soup.form_encode_hash(data)
            message = Soup.Message.new_from_encoded_form(method, url, form_data)
        else:
            message = Soup.Message.new(method, url)
        if data and not form:
            data = self.encode_data(data)
            message.set_request_body_from_bytes('application/json', data)
        if headers:
            for name, value in headers.items():
                message.get_request_headers().append(name, value)
        if 'User-Agent' not in headers:
            message.get_request_headers().append('User-Agent', 'Dialect App')
        return message

    def send_and_read(self, message: Soup.Message, callback: Callable[[Session, Gio.AsyncResult], None]):
        """
        Helper method for libsoup's send_and_read_async.

        Useful when priority and cancellable is not needed.

        Args:
            message: Message to send
            callback: Callback called from send_and_read_async to finish request
        """
        Session.get().send_and_read_async(message, 0, None, callback)

    def read_data(self, data: bytes) -> dict:
        """
        Get JSON data from bytes.

        Args:
            data: Bytes to read
        """
        return json.loads(data) if data else {}

    def read_response(self, session: Session, result: Gio.AsyncResult) -> dict:
        """
        Get JSON data from session result.

        Finishes request from send_and_read_async and gets body dict.

        Args:
            session: Session where the request wa sent
            result: Result of send_and_read_async callback
        """
        response = session.get_response(session, result)
        return self.read_data(response)

    def check_known_errors(self, status: Soup.Status, data: dict) -> None | ProviderError:
        """
        Checks data for possible response errors and return a found error if any.

        This should be implemented by subclases.

        Args:
            data: Response body data
        """
        return None

    def process_response(
        self,
        session: Session,
        result: Gio.AsyncResult,
        message: Soup.Message,
        on_continue: Callable[[dict | bytes], None],
        on_fail: Callable[[ProviderError], None],
        check_common: bool = True,
        json: bool = True,
    ):
        """
        Helper method for the most common workflow for processing soup responses.

        Checks for soup errors, then checks for common errors on data and calls on_fail
        if any, otherwise calls on_continue where the provider will finish the process.

        If json is false check_common is ignored and the data isn't processed as JSON and bites are passed to
        on_continue.

        Args:
            session: Session where the request wa sent
            result: Result of send_and_read_async callback
            message: The message that was sent
            on_continue: Called after data was got successfully
            on_fail: Called after any error on request or in check_known_errors
            check_common: If response data should be checked for errors using check_known_errors
            json: If data should be processed as JSON using read_response
        """

        try:
            if json:
                data = self.read_response(session, result)
            else:
                data = Session.get_response(session, result)

            if check_common:
                error = self.check_known_errors(message.get_status(), data)
                if error:
                    on_fail(error)
                    return

            on_continue(data)

        except Exception as exc:
            logging.warning(exc)
            on_fail(ProviderError(ProviderErrorCode.NETWORK, str(exc)))

    def send_and_read_and_process_response(
        self,
        message: Soup.Message,
        on_continue: Callable[[dict | bytes], None],
        on_fail: Callable[[ProviderError], None],
        check_common: bool = True,
        json: bool = True,
    ):
        """
        Helper packaging send_and_read and process_response.

        Avoids providers having to deal with many callbacks.

        message: Message to send
        on_continue: Called after data was got successfully
        on_fail: Called after any error on request or in check_known_errors
        check_common: If response data should be checked for errors using check_known_errors
        json: If data should be processed as JSON using read_response
        """

        def on_response(session: Session, result: Gio.AsyncResult):
            self.process_response(session, result, message, on_continue, on_fail, check_common, json)

        self.send_and_read(message, on_response)
