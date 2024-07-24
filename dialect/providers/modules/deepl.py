# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
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

API_V = "v2"


class Provider(SoupProvider):
    name = "deepl"
    prettyname = "DeepL"

    capabilities = ProviderCapability.TRANSLATION
    features = (
        ProviderFeature.DETECTION
        | ProviderFeature.API_KEY
        | ProviderFeature.API_KEY_REQUIRED
        | ProviderFeature.API_KEY_USAGE
    )

    defaults = {
        "instance_url": "",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en-US"],
    }

    _api_free = "api-free.deepl.com"
    _api_pro = "api.deepl.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 5000

        # DeepL API Free keys can be identified by the suffix ":fx"
        self.api_url = self.__get_api_url(self.api_key)

    def __get_api_url(self, api_key: str) -> str:
        return self._api_free if api_key.endswith(":fx") else self._api_pro

    @property
    def source_lang_url(self):
        return self.format_url(self.api_url, f"/{API_V}/languages", {"type": "source"})

    @property
    def target_lang_url(self):
        return self.format_url(self.api_url, f"/{API_V}/languages", {"type": "target"})

    @property
    def translate_url(self):
        return self.format_url(self.api_url, f"/{API_V}/translate")

    @property
    def usage_url(self):
        return self.format_url(self.api_url, f"/{API_V}/usage")

    @property
    def headers(self):
        return {"Authorization": f"DeepL-Auth-Key {self.api_key}"}

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

        def on_languages_response(data, type_):
            try:
                trans_src = type_ == "src"
                trans_dest = type_ == "dest"

                for lang in data:
                    self.add_lang(lang["language"], lang["name"], trans_src=trans_src, trans_dest=trans_dest)

                check_finished()

            except Exception as exc:
                print(type_)
                logging.warning(exc)
                on_failed(ProviderError(ProviderErrorCode.UNEXPECTED, str(exc)))

        # Keep state of multiple request
        self._init_count = 2
        self._init_error = None

        # Request messages
        src_langs_message = self.create_message("GET", self.source_lang_url, headers=self.headers)
        dest_langs_message = self.create_message("GET", self.target_lang_url, headers=self.headers)

        # Do async requests
        self.send_and_read_and_process_response(src_langs_message, lambda d: on_languages_response(d, "src"), on_failed)
        self.send_and_read_and_process_response(
            dest_langs_message, lambda d: on_languages_response(d, "dest"), on_failed
        )

    def validate_api_key(self, key, on_done, on_fail):
        def on_response(_data):
            on_done(True)

        api_url = self.__get_api_url(key)
        url = self.format_url(api_url, f"/{API_V}/languages", {"type": "source"})
        # Headers
        headers = {"Authorization": f"DeepL-Auth-Key {key}"}
        # Request messages
        languages_message = self.create_message("GET", url, headers=headers)
        # Do async requests
        self.send_and_read_and_process_response(languages_message, on_response, on_fail)

    def translate(self, text, src, dest, on_done, on_fail):
        def on_response(data):
            try:
                translations = data.get("translations")
                detected = translations[0].get("detected_source_language")
                translation = Translation(translations[0]["text"], (text, src, dest), detected)
                on_done(translation)

            except Exception as exc:
                logging.warning(exc)
                on_fail(ProviderError(ProviderErrorCode.TRANSLATION_FAILED, str(exc)))

        # Request body
        data = {
            "text": [text],
            "target_lang": dest,
        }
        if src != "auto":
            data["source_lang"] = src

        # Request message
        message = self.create_message("POST", self.translate_url, data, self.headers)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def api_char_usage(self, on_done, on_fail):
        def on_response(data):
            try:
                usage = data.get("character_count")
                limit = data.get("character_limit")
                on_done(usage, limit)

            except Exception as exc:
                logging.warning(exc)
                on_fail(ProviderError(ProviderErrorCode.UNEXPECTED, str(exc)))

        # Request message
        message = self.create_message("GET", self.usage_url, headers=self.headers)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def cmp_langs(self, a, b):
        # Early return if both langs are just the same
        if a == b:
            return True

        # Split lang code to separate it from possible country/script code
        a_codes = a.split("-")
        b_codes = b.split("-")

        if a_codes[0] == b_codes[0]:  # Check base codes
            return True

        return False

    def check_known_errors(self, status, data):
        message = data.get("message", "") if isinstance(data, dict) else ""

        match status:
            case 403:
                if not self.api_key:
                    return ProviderError(ProviderErrorCode.API_KEY_REQUIRED, message)
                return ProviderError(ProviderErrorCode.API_KEY_INVALID, message)
            case 456:
                return ProviderError(ProviderErrorCode.SERVICE_LIMIT_REACHED, message)

        if status != 200:
            return ProviderError(ProviderErrorCode.UNEXPECTED, message)
