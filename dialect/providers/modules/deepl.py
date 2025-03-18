# Copyright 2024 Mufeed Ali
# Copyright 2024 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from dialect.providers.base import ProviderCapability, ProviderFeature, ProviderLangComparison, Translation
from dialect.providers.errors import APIKeyInvalid, APIKeyRequired, ServiceLimitReached, UnexpectedError
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
    lang_comp = ProviderLangComparison.DEEP

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

    async def init_trans(self):
        # Get languages
        src_langs = await self.get(self.source_lang_url, self.headers)
        dest_langs = await self.get(self.target_lang_url, self.headers)

        if src_langs and dest_langs and isinstance(src_langs, list) and isinstance(dest_langs, list):
            for lang in src_langs:
                self.add_lang(lang["language"], lang["name"], trans_dest=False)
            for lang in src_langs:
                self.add_lang(lang["language"], lang["name"], trans_src=False)

    async def validate_api_key(self, key):
        api_url = self.__get_api_url(key)
        url = self.format_url(api_url, f"/{API_V}/languages", {"type": "source"})
        headers = {"Authorization": f"DeepL-Auth-Key {key}"}

        try:
            await self.get(url, headers)
            return True
        except (APIKeyInvalid, APIKeyRequired):
            return False
        except Exception:
            raise

    async def translate(self, request):
        src, dest = self.denormalize_lang(request.src, request.dest)

        # Request body
        data = {
            "text": [request.text],
            "target_lang": dest,
        }
        if src != "auto":
            data["source_lang"] = src

        response = await self.post(self.translate_url, data, self.headers)

        # Read translation
        if response and isinstance(response, dict):
            translations: list[dict[str, str]] | None = response.get("translations")
            if translations:
                detected = translations[0].get("detected_source_language")
                translation = Translation(translations[0]["text"], request, detected)
                return translation

        raise UnexpectedError

    async def api_char_usage(self):
        response = await self.get(self.usage_url, self.headers)

        try:
            usage = response.get("character_count")
            limit = response.get("character_limit")

            return usage, limit

        except Exception as exc:
            raise UnexpectedError from exc

    def check_known_errors(self, status, data):
        message = data.get("message", "") if isinstance(data, dict) else ""

        match status:
            case 403:
                if not self.api_key:
                    raise APIKeyRequired(message)
                raise APIKeyInvalid(message)
            case 456:
                raise ServiceLimitReached(message)

        if status != 200:
            raise UnexpectedError(message)

        if not data:
            raise UnexpectedError
