# Copyright 2023 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import re

from bs4 import BeautifulSoup

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    ProviderError,
    ProviderErrorCode,
    Translation,
)
from dialect.providers.soup import SoupProvider
from dialect.session import Session


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

    def init_trans(self, on_done, on_fail):
        def on_response(data):
            if data:
                try:
                    soup = BeautifulSoup(data, "html.parser")

                    # Get Langs
                    langs = soup.find("optgroup", {"id": "t_tgtAllLang"})
                    for child in langs.findChildren():
                        if child.name == "option":
                            self.add_lang(child["value"], child.contents[0])

                    # Get IID
                    iid = soup.find("div", {"id": "rich_tta"})
                    self._iid = iid["data-iid"]

                    # Decode response bytes
                    data = data.decode("utf-8")

                    # Look for abuse prevention data
                    params = re.findall("var params_AbusePreventionHelper = \[(.*?)\];", data)[0]  # noqa
                    abuse_params = params.replace('"', "").split(",")
                    self._key = abuse_params[0]
                    self._token = abuse_params[1]

                    # Look for IG
                    self._ig = re.findall('IG:"(.*?)",', data)[0]

                    on_done()

                except Exception as exc:
                    error = "Failed parsing HTML from bing.com"
                    logging.warning(error, exc)
                    on_fail(ProviderError(ProviderErrorCode.NETWORK, error))

            else:
                on_fail(ProviderError(ProviderErrorCode.EMPTY, "Could not get HTML from bing.com"))

        # Message request to get bing's website html
        message = self.create_message("GET", self.html_url, headers=self._headers)

        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail, False, False)

    def translate(self, text, src, dest, on_done, on_fail):
        def on_response(data):
            try:
                data = data[0]
                detected = None
                pronunciation = None

                if "translations" in data:
                    if "detectedLanguage" in data:
                        detected = data["detectedLanguage"]["language"]

                    if "transliteration" in data["translations"][0]:
                        pronunciation = data["translations"][0]["transliteration"]["text"]

                    translation = Translation(
                        data["translations"][0]["text"],
                        (text, src, dest),
                        detected=detected,
                        pronunciation=(None, pronunciation),
                    )
                    on_done(translation)

            except Exception as exc:
                logging.warning(exc)
                on_fail(ProviderError(ProviderErrorCode.TRANSLATION_FAILED, str(exc)))

        # Increment requests count
        self._count += 1

        # Form data
        data = {
            "fromLang": "auto-detect" if src == "auto" else src,
            "text": text,
            "to": dest,
            "token": self._token,
            "key": self._key,
        }
        # Request message
        message = self.create_message("POST", self.translate_url, data, self._headers, True)
        # Do async request
        self.send_and_read_and_process_response(message, on_response, on_fail)

    def check_known_errors(self, _status, data):
        if not data:
            return ProviderError(ProviderErrorCode.EMPTY, "Response is empty!")

        if "errorMessage" in data:
            error = data["errorMessage"]
            code = data["statusCode"]

            match code:
                case _:
                    return ProviderError(ProviderErrorCode.UNEXPECTED, error)

        return None
