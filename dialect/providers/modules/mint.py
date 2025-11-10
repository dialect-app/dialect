# Copyright 2021 Mufeed Ali
# Copyright 2021 Rafael Mardojai CM
# Copyright 2025 Alejandro Armas
# SPDX-License-Identifier: GPL-3.0-or-later

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    Translation,
)
from dialect.providers.errors import (
    UnexpectedError,
)
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "mint"
    prettyname = "MinT"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.INSTANCES

    defaults = {
        "instance_url": "translate.wmcloud.org",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.src_dest_langs = dict()

    @property
    def lang_url(self):
        return self.format_url(self.instance_url, "/api/languages")

    @property
    def translate_url(self):
        return self.format_url(self.instance_url, "/api/translate")

    def cmp_langs(self, a: str, b: str) -> bool:
        """
        Compare two language codes.

        Args:
            a: First lang to compare.
            b: Second lang to compare.

        Returns:
            True if it's not possible to translate from a to b.
        """
        valid_dests = self.src_dest_langs.get(a, [])
        return not b in valid_dests

    async def init_trans(self):
        response = await self.get(self.lang_url)

        try:
            for src_lang, dest_langs in response.items():
                src_lang = self.normalize_lang_code(src_lang)
                self.add_lang(src_lang)
                self.src_dest_langs[src_lang] = [self.normalize_lang_code(l) for l in dest_langs.keys()]

        except Exception as exc:
            raise UnexpectedError from exc

    async def translate(self, request):
        src, dest = self.denormalize_lang(request.src, request.dest)

        # Request body
        data = {
            "content": request.text,
            "format": "text",
            "source_language": src,
            "target_language": dest,
        }

        # Do request
        response = await self.post(self.translate_url, data)

        try:
            return Translation(response["translation"], request)
        except Exception as exc:
            raise UnexpectedError from exc
