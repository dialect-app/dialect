# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from bs4 import BeautifulSoup, Tag

from dialect.providers.base import ProviderCapability, ProviderFeature, Translation, TranslationPronunciation
from dialect.providers.errors import ProviderError, UnexpectedError
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "bing"
    prettyname = "Bing"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.DETECTION | ProviderFeature.PRONUNCIATION

    defaults = {
        "instance_url": "",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de"],
        "dest_langs": ["fr", "es", "de", "en"],
    }

    _headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "*/*"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = 1000  # Web UI limit

        # Session vars
        self._key = ""
        self._token = ""
        self._ig = ""
        self._iid = ""
        self._count = 1

    @property
    def html_url(self):
        return self.format_url("www.bing.com", "/translator")

    @property
    def translate_url(self):
        params = {
            "isVertical": "1",
            "": "",
            "IG": self._ig,
            "IID": f"{self._iid}.{self._count}",
        }
        return self.format_url("www.bing.com", "/ttranslatev3", params)

    async def init_trans(self):
        response = await self.get(self.html_url, self._headers, check_common=False, return_json=False)

        if response:
            try:
                soup = BeautifulSoup(response, "html.parser")

                # Get Langs
                langs = soup.find("optgroup", {"id": "t_tgtAllLang"})
                if isinstance(langs, Tag):
                    for child in langs.findChildren():
                        if child.name == "option":
                            self.add_lang(child["value"], child.contents[0])

                # Get IID
                iid = soup.find("div", {"id": "rich_tta"})
                if isinstance(iid, Tag):
                    self._iid = iid["data-iid"]

                # Decode response bytes
                text = response.decode("utf-8")

                # Look for abuse prevention data
                params = re.findall(r"var params_AbusePreventionHelper = \[(.*?)\];", text)[0]  # noqa
                abuse_params = params.replace('"', "").split(",")
                self._key = abuse_params[0]
                self._token = abuse_params[1]

                # Look for IG
                self._ig = re.findall('IG:"(.*?)",', text)[0]

            except Exception as exc:
                raise UnexpectedError("Failed parsing HTML from bing.com") from exc

        else:
            raise UnexpectedError("Could not get HTML from bing.com")

    async def translate(self, request):
        src, dest = self.denormalize_lang(request.src, request.dest)

        # Increment requests count
        self._count += 1

        # Form data
        data = {
            "fromLang": "auto-detect" if src == "auto" else src,
            "text": request.text,
            "to": dest,
            "token": self._token,
            "key": self._key,
        }

        # Do request
        response = await self.post(self.translate_url, data, self._headers, True)

        try:
            data = response[0]
            detected = None
            pronunciation = None

            if "translations" in data:
                if "detectedLanguage" in data:
                    detected = data["detectedLanguage"]["language"]

                if "transliteration" in data["translations"][0]:
                    pronunciation = data["translations"][0]["transliteration"]["text"]

                return Translation(
                    data["translations"][0]["text"],
                    request,
                    detected=detected,
                    pronunciation=TranslationPronunciation(None, pronunciation),
                )
            else:
                raise UnexpectedError("Unexpected translation response")

        except Exception as exc:
            raise UnexpectedError from exc

    def check_known_errors(self, status, data):
        if not data:
            raise UnexpectedError("Response is empty!")

        if "errorMessage" in data:
            error = data["errorMessage"]
            code = data["statusCode"]

            match code:
                case _:
                    raise ProviderError(error)

        return None
