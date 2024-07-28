# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from uuid import uuid4

from dialect.providers.base import (
    ProviderCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderFeature,
    Translation,
)
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

    def init_trans(self, on_done, on_fail):
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

        on_done()

    @property
    def translate_url(self):
        path = f"/api/v1/tr.json/translate?id={self._uuid}-0-0&srv=android"
        return self.format_url("translate.yandex.net", path)

    def translate(self, text, src, dest, on_done, on_fail):
        def on_response(data: dict):
            detected = None
            if "code" in data and data["code"] == 200:
                if "lang" in data:
                    detected = data["lang"].split("-")[0]

                if "text" in data:
                    translation = Translation(data["text"][0], (text, src, dest), detected)
                    on_done(translation)

                else:
                    on_fail(ProviderError(ProviderErrorCode.TRANSLATION_FAILED, "Translation failed"))

            else:
                error = data["message"] if "message" in data else ""
                on_fail(ProviderError(ProviderErrorCode.TRANSLATION_FAILED, error))

        # Form data
        data = {"lang": dest, "text": text}
        if src != "auto":
            data["lang"] = f"{src}-{dest}"

        # Request message
        message = self.create_message("POST", self.translate_url, data, self._headers, True)

        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)
