# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from tempfile import NamedTemporaryFile
from urllib.parse import quote

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    Translation,
    TranslationMistake,
    TranslationPronunciation,
)
from dialect.providers.errors import InvalidLangCode, UnexpectedError
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

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, "/api/v1/languages/")

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, "/api/v1/{src}/{dest}/{text}")

    @property
    def speech_url(self):
        return self.format_url(self.instance_url, "/api/v1/audio/{lang}/{text}")

    async def validate_instance(self, url):
        request = await self.get(self.format_url(url, "/api/v1/en/es/hello"), check_common=False)

        valid = False
        try:
            valid = "translation" in request
        except:  # noqa
            pass

        return valid

    async def init(self) -> None:
        response = await self.get(self.lang_url)

        try:
            if "languages" in response:
                for lang in response["languages"]:
                    if lang["code"] != "auto":
                        self.add_lang(lang["code"], lang["name"], tts=True)
            else:
                raise UnexpectedError("No langs found in server.")
        except Exception as exc:
            raise UnexpectedError from exc

    async def init_trans(self):
        await self.init()

    async def init_tts(self):
        await self.init()

    async def translate(self, request):
        src, dest = self.denormalize_lang(request.src, request.dest)
        # Format url query data
        text = quote(request.text, safe="")
        url = self.translate_url.format(text=text, src=src, dest=dest)

        # Do request
        response = await self.get(url)
        try:
            detected = response.get("info", {}).get("detectedSource", None)
            mistakes = response.get("info", {}).get("typo", None)
            src_pronunciation = response.get("info", {}).get("pronunciation", {}).get("query", None)
            dest_pronunciation = response.get("info", {}).get("pronunciation", {}).get("translation", None)

            return Translation(
                response["translation"],
                request,
                detected,
                TranslationMistake(mistakes, mistakes) if mistakes else None,
                TranslationPronunciation(src_pronunciation, dest_pronunciation),
            )

        except Exception as exc:
            raise UnexpectedError("Failed reading the translation data") from exc

    async def speech(self, text, language):
        (language,) = self.denormalize_lang(language)
        # Format url query data
        url = self.speech_url.format(text=text, lang=language)
        # Do request
        response = await self.get(url)

        try:
            file = NamedTemporaryFile()
            audio = bytearray(response["audio"])
            file.write(audio)
            file.seek(0)
            return file
        except Exception as exc:
            file.close()
            raise UnexpectedError from exc

    def check_known_errors(self, status, data):
        """Raises a proper Exception if an error is found in the data."""
        if not data:
            raise UnexpectedError("Response is empty!")

        if "error" in data:
            error = data["error"]

            if error == "Invalid target language" or error == "Invalid source language":
                raise InvalidLangCode(error)
            else:
                raise UnexpectedError(error)
