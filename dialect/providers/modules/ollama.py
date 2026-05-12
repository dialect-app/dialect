# Copyright 2026 Sunur Efe Vural
# SPDX-License-Identifier: GPL-3.0-or-later

import json

from dialect.define import LANGUAGES as ALL_LANGUAGES
from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    TranslationRequest,
)
from dialect.providers.errors import RequestError
from dialect.providers.soup import SoupProvider
from dialect.session import Session

AUTO_PROMPT = (
    "You are a professional {dest_lang} ({dest_code}) translator. Your goal is to"
    " accurately convey the meaning and nuances of the original text while adhering"
    " to {dest_lang} grammar, vocabulary, and cultural sensitivities.\n"
    "Produce only the {dest_lang} translation, without any additional explanations or"
    " commentary. Please translate the following text into {dest_lang}:\n\n\n"
)

TRANSLATE_PROMPT = (
    "You are a professional {src_lang} ({src_code}) to {dest_lang} ({dest_code})"
    " translator. Your goal is to accurately convey the meaning and nuances of the"
    " original {src_lang} text while adhering to {dest_lang} grammar, vocabulary,"
    " and cultural sensitivities.\n"
    "Produce only the {dest_lang} translation, without any additional explanations or"
    " commentary. Please translate the following {src_lang} text into {dest_lang}:\n\n\n"
)

SUPPORTED_LANGS = [
    "zh",
    "en",
    "fr",
    "pt",
    "es",
    "ja",
    "tr",
    "ru",
    "ar",
    "ko",
    "th",
    "it",
    "de",
    "vi",
    "ms",
    "id",
    "tl",
    "hi",
    "pl",
    "cs",
    "nl",
    "km",
    "my",
    "fa",
    "gu",
    "ur",
    "te",
    "mr",
    "he",
    "bn",
    "ta",
    "uk",
    "bo",
    "kk",
    "mn",
    "ug",
    "yue",
]


class Provider(SoupProvider):
    name = "ollama"
    prettyname = "Ollama"

    capabilities = ProviderCapability.TRANSLATION
    features = (
        ProviderFeature.INSTANCES
        | ProviderFeature.ENGINES
        | ProviderFeature.DETECTION
        | ProviderFeature.API_KEY
        | ProviderFeature.STREAMING
    )

    defaults = {
        "instance_url": "localhost:11434/api",
        "engine_name": "translategemma",
        "api_key": "",
        "src_langs": [],
        "dest_langs": ["en"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def generate_url(self):
        return self.format_url(self.instance_url, "/generate")

    @property
    def headers(self) -> dict:
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def _fetch_model_names(self, url) -> list[str]:
        response = await self.get(self.format_url(url, "/tags"), self.headers, check_common=False)
        return [m["name"] for m in response.get("models", [])]

    async def validate_instance(self, url):
        try:
            return bool(await self._fetch_model_names(url))
        except Exception:
            return False

    async def validate_engine(self, name):
        try:
            available = await self._fetch_model_names(self.instance_url)
            engine = name if ":" in name else name + ":latest"
            return engine in available
        except Exception:
            return False

    async def init_trans(self):
        available = await self._fetch_model_names(self.instance_url)
        if not available:
            raise RequestError("Ollama instance not reachable or has no models")
        engine = self.engine if ":" in self.engine else self.engine + ":latest"
        if engine not in available:
            raise RequestError(f'Model "{self.engine}" is not available on this Ollama instance')
        for code in SUPPORTED_LANGS:
            self.add_lang(code, ALL_LANGUAGES.get(code))

    def _build_prompt(self, request: TranslationRequest) -> str:
        dest_lang = self._languages_names.get(request.dest, request.dest)

        if request.src == "auto":
            return AUTO_PROMPT.format(dest_lang=dest_lang, dest_code=request.dest) + request.text
        else:
            src_lang = self._languages_names.get(request.src, request.src)
            prompt = TRANSLATE_PROMPT.format(
                src_lang=src_lang,
                src_code=request.src,
                dest_lang=dest_lang,
                dest_code=request.dest,
            )
            return prompt + request.text

    async def stream_translate(self, request: TranslationRequest):
        from gi.repository import Gio

        prompt = self._build_prompt(request)
        data = {"model": self.engine, "prompt": prompt, "stream": True}
        message = self.create_message("POST", self.generate_url, data, self.headers)

        try:
            stream = Gio.DataInputStream.new(await Session.get().send_async(message, 0, None))
            while True:
                line, _ = await stream.read_line_async(0, None)
                if not line:
                    break
                obj = json.loads(line)
                if token := obj.get("response"):
                    yield token
                if obj.get("done", False):
                    return
        except Exception as exc:
            raise RequestError(str(exc)) from exc

    def check_known_errors(self, status, data):
        pass
