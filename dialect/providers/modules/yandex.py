# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re
from uuid import uuid4

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    ProviderLangComparison,
    Translation,
)
from dialect.providers.errors import ProviderError, UnexpectedError
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "yandex"
    prettyname = "Yandex"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.DETECTION
    lang_comp = ProviderLangComparison.DEEP

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

    @property
    def translate_url(self):
        params = {"id": self._uuid + "-0-0", "srv": "android"}
        return self.format_url("translate.yandex.net", "/api/v1/tr.json/translate", params)

    async def init_trans(self):
        # Get Yandex Translate web HTML to parse languages
        # Using `/api/v1/tr.json/getLangs` doesn't provide all the languages that Yandex supports
        html_url = self.format_url("translate.yandex.com")
        response = await self.get(html_url, check_common=False, return_json=False)

        if response:
            try:
                # Decode response bytes
                text = response.decode("utf-8")
                # Get Yandex languages
                languages = re.findall(r"TRANSLATOR_LANGS: (.*?),\n", text)[0]  # noqa
                languages: dict[str, str] = json.loads(languages)  # type: ignore
                # Get Yandex dialects list, dialects aren't valid src tranlation langs
                dialects = re.findall(r"DIALECTS: (.*?),\n", text)[0]  # noqa
                dialects: list[str] = json.loads(dialects)  # type: ignore
                # Populate languages lists
                for code, name in languages.items():
                    self.add_lang(code, name, trans_src=code not in dialects)

            except Exception as exc:
                raise UnexpectedError("Failed parsing HTML from yandex.com") from exc
        else:
            raise UnexpectedError("Could not get HTML from yandex.com")

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
