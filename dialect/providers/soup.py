# Copyright 2022 Mufeed Ali
# Copyright 2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import logging
from asyncio import sleep
from typing import Any

from gi.repository import GLib, Soup

from dialect.providers.base import BaseProvider
from dialect.providers.errors import RequestError
from dialect.session import Session


class SoupProvider(BaseProvider):
    """Base class for providers needing libsoup helpers"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.retry_errors: tuple[int] = tuple()
        """ Error codes that should be retried automatically """
        self.max_retries = 5
        """ Max number of tries """

    def encode_data(self, data: Any) -> GLib.Bytes | None:
        """
        Convert Python data to JSON and bytes.

        Args:
            data: Data to encode, anything json.dumps can handle.

        Returns:
            The GLib Bytes or None if something failed.
        """
        data_glib_bytes = None
        try:
            data_bytes = json.dumps(data).encode("utf-8")
            data_glib_bytes = GLib.Bytes.new(data_bytes)
        except Exception as exc:
            logging.warning(exc)
        return data_glib_bytes

    def create_message(
        self, method: str, url: str, data: Any = {}, headers: dict = {}, form: bool = False
    ) -> Soup.Message:
        """
        Create a Soup's message.

        Encodes data and adds it to the message as the request body.

        Args:
            method: HTTP method of the message.
            url: Url of the message.
            data: Request body or form data.
            headers: HTTP headers of the message.
            form: If the data should be encoded as ``application/x-www-form-urlencoded``.

        Returns:
            The Soup Message for the given parameters.
        """

        if form and data:
            form_data = Soup.form_encode_hash(data)
            message = Soup.Message.new_from_encoded_form(method, url, form_data)
        else:
            message = Soup.Message.new(method, url)

        if message:
            if data and not form:
                data = self.encode_data(data)
                message.set_request_body_from_bytes("application/json", data)
            if headers:
                for name, value in headers.items():
                    message.get_request_headers().append(name, value)
            if "User-Agent" not in headers:
                message.get_request_headers().append("User-Agent", "Dialect App")

        return message  # type: ignore

    async def send_and_read(self, message: Soup.Message) -> bytes | None:
        """
        Helper method for Soup's send_and_read_async.

        Args:
            message: Message to send.

        Returns:
            The bytes of the response or None.
        """
        response: GLib.Bytes = await Session.get().send_and_read_async(message, 0)  # type: ignore
        return response.get_data()

    async def send_and_read_json(self, message: Soup.Message) -> Any:
        """
        Like ``SoupProvider.send_and_read`` but returns JSON parsed.

        Args:
            message: Message to send.

        Returns:
            The JSON of the response deserialized to a python object.
        """
        response = await self.send_and_read(message)
        return json.loads(response) if response else {}

    def check_known_errors(self, status: Soup.Status, data: Any) -> None:
        """
        Checks data for possible response errors and raises appropriated exceptions.

        This should be implemented by subclases.

        Args:
            status: HTTP status.
            data: Response body data.
        """

    async def send_and_read_and_process(
        self,
        message: Soup.Message,
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper mixing ``SoupProvider.send_and_read``, ``SoupProvider.send_and_read_json``
        and ``SoupProvider.check_known_errors``.

        Converts `GLib.Error` to `RequestError`.

        It also handles retries for status codes listen in ``self.retry_errors``.

        Args:
            message: Message to send.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """

        async def send_and_read() -> Any:
            if return_json:
                return await self.send_and_read_json(message)
            else:
                return await self.send_and_read(message)

        try:
            response = await send_and_read()

            # Do retries with exponential backoff for errors
            if message.get_status() in self.retry_errors:
                delay = 1

                for _ in range(self.max_retries):
                    await sleep(delay)
                    response = await send_and_read()

                    if message.get_status() in self.retry_errors:
                        delay *= 2
                    else:
                        break

            if check_common:
                self.check_known_errors(message.get_status(), response)

            return response
        except GLib.Error as exc:
            raise RequestError(exc.message)

    async def request(
        self,
        method: str,
        url: str,
        data: Any = {},
        headers: dict = {},
        form: bool = False,
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper for regular HTTP request.

        Args:
            method: HTTP method of the request.
            url: Url of the request.
            data: Request body or form data.
            headers: HTTP headers of the message.
            form: If the data should be encoded as a form.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        message = self.create_message(method, url, data, headers, form)
        return await self.send_and_read_and_process(message, check_common, return_json)

    async def get(
        self,
        url: str,
        headers: dict = {},
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper for GET HTTP request.

        Args:
            url: Url of the request.
            headers: HTTP headers of the message.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        return await self.request("GET", url, headers=headers, check_common=check_common, return_json=return_json)

    async def post(
        self,
        url: str,
        data: Any = {},
        headers: dict = {},
        form: bool = False,
        check_common: bool = True,
        return_json: bool = True,
    ) -> Any:
        """
        Helper for POST HTTP request.

        Args:
            url: Url of the request.
            data: Request body or form data.
            headers: HTTP headers of the message.
            form: If the data should be encoded as a form.
            check_common: If response data should be checked for errors using check_known_errors.
            return_json: If the response should be parsed as JSON.

        Returns:
            The JSON deserialized to a python object or bytes if ``json`` is ``False``.
        """
        return await self.request("POST", url, data, headers, form, check_common, return_json)
