# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from uuid import uuid4

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    Translation,
)
from dialect.providers.errors import ProviderError, UnexpectedError
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "yandex"
    prettyname = "Yandex"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.DETECTION

    defaults = {
        "instance_url": "",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    _headers = {
        "User-Agent": "ru.yandex.translate/21.15.4.21402814 (Xiaomi Redmi K20 Pro; Android 11)",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 10000

        self._uuid = str(uuid4()).replace("-", "")

    async def init_trans(self):
        languages = [
            "af",
            "sq",
            "am",
            "ar",
            "hy",
            "az",
            "ba",
            "eu",
            "be",
            "bn",
            "bs",
            "bg",
            "my",
            "ca",
            "ceb",
            "zh",
            "cv",
            "hr",
            "cs",
            "da",
            "nl",
            "sjn",
            "emj",
            "en",
            "eo",
            "et",
            "fi",
            "fr",
            "gl",
            "ka",
            "de",
            "el",
            "gu",
            "ht",
            "he",
            "mrj",
            "hi",
            "hu",
            "is",
            "id",
            "ga",
            "it",
            "ja",
            "jv",
            "kn",
            "kk",
            "kazlat",
            "km",
            "ko",
            "ky",
            "lo",
            "la",
            "lv",
            "lt",
            "lb",
            "mk",
            "mg",
            "ms",
            "ml",
            "mt",
            "mi",
            "mr",
            "mhr",
            "mn",
            "ne",
            "no",
            "pap",
            "fa",
            "pl",
            "pt",
            "pt_BR",
            "pa",
            "ro",
            "ru",
            "gd",
            "sr",
            "si",
            "sk",
            "sl",
            "es",
            "su",
            "sw",
            "sv",
            "tl",
            "tg",
            "ta",
            "tt",
            "te",
            "th",
            "tr",
            "udm",
            "uk",
            "ur",
            "uz",
            "uzbcyr",
            "vi",
            "cy",
            "xh",
            "sah",
            "yi",
            "zu",
        ]
        for code in languages:
            self.add_lang(code)

    @property
    def translate_url(self):
        path = f"/api/v1/tr.json/translate?id={self._uuid}-0-0&srv=android"
        return self.format_url("translate.yandex.net", path)

    async def translate(self, request):
        src, dest = self.denormalize_lang(request.src, request.dest)
        # Form data
        data = {"lang": dest, "text": request.text}
        if src != "auto":
            data["lang"] = f"{src}-{dest}"

        # Do request
        response = await self.post(self.translate_url, data, self._headers, True)
        try:
            detected = None
            if "code" in response and response["code"] == 200:
                if "lang" in response:
                    detected = response["lang"].split("-")[0]
                return Translation(response["text"][0], request, detected)
            else:
                error = response["message"] if "message" in response else ""
                raise ProviderError(error)
        except Exception as exc:
            raise UnexpectedError from exc
