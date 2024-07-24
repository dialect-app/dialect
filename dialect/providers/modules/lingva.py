# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from tempfile import NamedTemporaryFile
from urllib.parse import quote

from dialect.providers.base import (
    ProviderCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderFeature,
    Translation,
)
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "lingva"
    prettyname = "Lingva Translate"

    capabilities = ProviderCapability.TRANSLATION | ProviderCapability.TTS
    features = (
        ProviderFeature.INSTANCES | ProviderFeature.DETECTION | ProviderFeature.MISTAKES | ProviderFeature.PRONUNCIATION
    )

    defaults = {
        "instance_url": "lingva.dialectapp.org",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 5000

    def validate_instance(self, url, on_done, on_fail):
        def on_response(data):
            valid = False
            try:
                valid = "translation" in data
            except:  # noqa
                pass

            on_done(valid)

        # Lingva translation endpoint
        message = self.create_message("GET", self.format_url(url, "/api/v1/en/es/hello"))
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail, False)

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, "/api/v1/languages/")

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, "/api/v1/{src}/{dest}/{text}")

    @property
    def speech_url(self):
        return self.format_url(self.instance_url, "/api/v1/audio/{lang}/{text}")

    def init(self, on_done, on_fail):
        def on_response(data):
            if "languages" in data:
                for lang in data["languages"]:
                    if lang["code"] != "auto":
                        self.add_lang(lang["code"], lang["name"], tts=True)
                on_done()
            else:
                on_fail(ProviderError(ProviderErrorCode.UNEXPECTED, "No langs found in server."))

        # Languages message request
        message = self.create_message("GET", self.lang_url)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def init_trans(self, on_done, on_fail):
        self.init(on_done, on_fail)

    def init_tts(self, on_done, on_fail):
        self.init(on_done, on_fail)

    def translate(self, text, src, dest, on_done, on_fail):
        def on_response(data):
            try:
                detected = data.get("info", {}).get("detectedSource", None)
                mistakes = data.get("info", {}).get("typo", None)
                src_pronunciation = data.get("info", {}).get("pronunciation", {}).get("query", None)
                dest_pronunciation = data.get("info", {}).get("pronunciation", {}).get("translation", None)

                translation = Translation(
                    data["translation"],
                    (text, src, dest),
                    detected,
                    (mistakes, mistakes),
                    (src_pronunciation, dest_pronunciation),
                )

                on_done(translation)

            except Exception as exc:
                error = "Failed reading the translation data"
                logging.warning(error, exc)
                on_fail(ProviderError(ProviderErrorCode.TRANSLATION_FAILED, error))

        # Format url query data
        text = quote(text, safe="")
        url = self.translate_url.format(text=text, src=src, dest=dest)

        # Request message
        message = self.create_message("GET", url)

        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def speech(self, text, language, on_done, on_fail):
        def on_response(data):
            if "audio" in data:
                file = NamedTemporaryFile()
                audio = bytearray(data["audio"])
                file.write(audio)
                file.seek(0)

                on_done(file)
            else:
                on_fail(ProviderError(ProviderErrorCode.TTS_FAILED, "No audio was found."))

        # Format url query data
        url = self.speech_url.format(text=text, lang=language)

        # Request message
        message = self.create_message("GET", url)

        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def check_known_errors(self, _status, data):
        """Raises a proper Exception if an error is found in the data."""
        if not data:
            return ProviderError(ProviderErrorCode.EMPTY, "Response is empty!")
        if "error" in data:
            error = data["error"]

            if error == "Invalid target language" or error == "Invalid source language":
                return ProviderError(ProviderErrorCode.INVALID_LANG_CODE, error)
            else:
                return ProviderError(ProviderErrorCode.UNEXPECTED, error)
