# Copyright 2021-2022 Mufeed Ali
# Copyright 2021-2022 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    ProviderErrorCode,
    ProviderError,
    Translation,
)
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "libretranslate"
    prettyname = "LibreTranslate"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.INSTANCES | ProviderFeature.DETECTION | ProviderFeature.PRONUNCIATION

    defaults = {
        "instance_url": "lt.dialectapp.org",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 0

    def validate_instance(self, url, on_done, on_fail):
        def on_response(data):
            valid = False

            try:
                valid = data["info"]["title"] == "LibreTranslate"
            except:  # noqa
                pass

            on_done(valid)

        # Message request to LT API spec endpoint
        message = self.create_message("GET", self.format_url(url, "/spec"))
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail, False)

    @property
    def frontend_settings_url(self):
        return self.format_url(self.instance_url, "/frontend/settings")

    @property
    def detect_url(self):
        return self.format_url(self.instance_url, "/detect")

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, "/languages")

    @property
    def suggest_url(self):
        return self.format_url(self.instance_url, "/suggest")

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, "/translate")

    def init_trans(self, on_done, on_fail):
        def check_finished():
            self._init_count -= 1

            if self._init_count == 0:
                if self._init_error:
                    on_fail(self._init_error)
                else:
                    on_done()

        def on_failed(error):
            self._init_error = error
            check_finished()

        def on_languages_response(data):
            try:
                for lang in data:
                    self.add_lang(lang["code"], lang["name"])

                check_finished()

            except Exception as exc:
                logging.warning(exc)
                on_failed(ProviderError(ProviderErrorCode.UNEXPECTED, str(exc)))

        def on_settings_response(data):
            try:
                if data.get("suggestions", False):
                    self.features ^= ProviderFeature.SUGGESTIONS
                if data.get("apiKeys", False):
                    self.features ^= ProviderFeature.API_KEY
                if data.get("keyRequired", False):
                    self.features ^= ProviderFeature.API_KEY_REQUIRED

                self.chars_limit = data.get("charLimit", 0)

                check_finished()

            except Exception as exc:
                logging.warning(exc)
                on_failed(ProviderError(ProviderErrorCode.UNEXPECTED, str(exc)))

        # Keep state of multiple request
        self._init_count = 2
        self._init_error = None

        # Request messages
        languages_message = self.create_message("GET", self.lang_url)
        settings_message = self.create_message("GET", self.frontend_settings_url)

        # Do async requests
        self.send_and_read_and_process_response(languages_message, on_languages_response, on_failed)
        self.send_and_read_and_process_response(settings_message, on_settings_response, on_failed)

    def validate_api_key(self, key, on_done, on_fail):
        def on_response(data):
            valid = False
            try:
                valid = "confidence" in data[0]
            except:  # noqa
                pass

            on_done(valid)

        # Form data
        data = {
            "q": "hello",
            "api_key": key,
        }

        # Request message
        message = self.create_message("POST", self.detect_url, data, form=True)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def translate(self, text, src, dest, on_done, on_fail):
        def on_response(data):
            detected = data.get("detectedLanguage", {}).get("language", None)
            translation = Translation(data["translatedText"], (text, src, dest), detected)
            on_done(translation)

        # Request body
        data = {
            "q": text,
            "source": src,
            "target": dest,
        }
        if self.api_key and ProviderFeature.API_KEY in self.features:
            data["api_key"] = self.api_key

        # Request message
        message = self.create_message("POST", self.translate_url, data)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def suggest(self, text, src, dest, suggestion, on_done, on_fail):
        def on_response(data):
            on_done(data.get("success", False))

        # Form data
        data = {
            "q": text,
            "source": src,
            "target": dest,
            "s": suggestion,
        }
        if self.api_key and ProviderFeature.API_KEY in self.features:
            data["api_key"] = self.api_key

        # Request message
        message = self.create_message("POST", self.suggest_url, data, form=True)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def check_known_errors(self, _status, data):
        if not data:
            return ProviderError(ProviderErrorCode.EMPTY, "Response is empty!")
        if "error" in data:
            error = data["error"]

            if error == "Please contact the server operator to obtain an API key":
                return ProviderError(ProviderErrorCode.API_KEY_REQUIRED, error)
            elif error == "Invalid API key":
                return ProviderError(ProviderErrorCode.API_KEY_INVALID, error)
            elif "is not supported" in error:
                return ProviderError(ProviderErrorCode.INVALID_LANG_CODE, error)
            elif "exceeds text limit" in error:
                return ProviderError(ProviderErrorCode.BATCH_SIZE_EXCEEDED, error)
            elif "exceeds character limit" in error:
                return ProviderError(ProviderErrorCode.CHARACTERS_LIMIT_EXCEEDED, error)
            elif "Cannot translate text" in error or "format is not supported" in error:
                return ProviderError(ProviderErrorCode.TRANSLATION_FAILED, error)
            else:
                return ProviderError(ProviderErrorCode.UNEXPECTED, error)
