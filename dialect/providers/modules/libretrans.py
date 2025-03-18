# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    Translation,
)
from dialect.providers.errors import (
    APIKeyInvalid,
    APIKeyRequired,
    BatchSizeExceeded,
    CharactersLimitExceeded,
    InvalidLangCode,
    UnexpectedError,
)
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "libretranslate"
    prettyname = "LibreTranslate"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.INSTANCES | ProviderFeature.DETECTION

    defaults = {
        "instance_url": "lt.dialectapp.org",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 0

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

    async def validate_instance(self, url):
        response = await self.get(self.format_url(url, "/spec"), check_common=False)
        valid = False

        try:
            valid = response["info"]["title"] == "LibreTranslate"
        except:  # noqa
            pass

        return valid

    async def validate_api_key(self, key):
        # Form data
        data = {
            "q": "hello",
            "api_key": key,
        }

        try:
            response = await self.post(self.detect_url, data, form=True)
            return "confidence" in response[0]
        except (APIKeyInvalid, APIKeyRequired):
            return False
        except Exception:
            raise

    async def init_trans(self):
        languages = await self.get(self.lang_url)
        settings = await self.get(self.frontend_settings_url)

        try:
            for lang in languages:
                self.add_lang(lang["code"], lang["name"])

            if settings.get("suggestions", False):
                self.features ^= ProviderFeature.SUGGESTIONS
            if settings.get("apiKeys", False):
                self.features ^= ProviderFeature.API_KEY
            if settings.get("keyRequired", False):
                self.features ^= ProviderFeature.API_KEY_REQUIRED

            self.chars_limit = int(settings.get("charLimit", 0))

        except Exception as exc:
            raise UnexpectedError from exc

    async def translate(self, request):
        src, dest = self.denormalize_lang(request.src, request.dest)

        # Request body
        data = {
            "q": request.text,
            "source": src,
            "target": dest,
        }
        if self.api_key and ProviderFeature.API_KEY in self.features:
            data["api_key"] = self.api_key

        # Do request
        response = await self.post(self.translate_url, data)
        try:
            detected = response.get("detectedLanguage", {}).get("language", None)
            return Translation(response["translatedText"], request, detected)
        except Exception as exc:
            raise UnexpectedError from exc

    async def suggest(self, text, src, dest, suggestion):
        src, dest = self.denormalize_lang(src, dest)

        # Form data
        data = {
            "q": text,
            "source": src,
            "target": dest,
            "s": suggestion,
        }
        if self.api_key and ProviderFeature.API_KEY in self.features:
            data["api_key"] = self.api_key

        # Do request
        response = await self.post(self.suggest_url, data, form=True)
        try:
            return response.get("success", False)
        except:  # noqa
            return False

    def check_known_errors(self, status, data):
        if not data:
            raise UnexpectedError("Response is empty!")

        if "error" in data:
            error = data["error"]

            if error == "Please contact the server operator to obtain an API key":
                raise APIKeyRequired(error)
            elif error == "Invalid API key":
                raise APIKeyInvalid(error)
            elif "is not supported" in error:
                raise InvalidLangCode(error)
            elif "exceeds text limit" in error:
                raise BatchSizeExceeded(error)
            elif "exceeds character limit" in error:
                raise CharactersLimitExceeded(error)
            else:
                raise UnexpectedError(error)
