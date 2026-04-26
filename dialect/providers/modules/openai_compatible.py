# Copyright 2026 Dialect contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re
from typing import Any

from gi.repository import Gio, GLib

from dialect.define import APP_ID, LANGUAGES
from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    Translation,
    TranslationRequest,
)
from dialect.providers.errors import (
    APIKeyInvalid,
    APIKeyRequired,
    RequestError,
    ServiceLimitReached,
    UnexpectedError,
)
from dialect.providers.settings import ProviderDefaults
from dialect.providers.soup import SoupProvider

_DEFAULT_PROMPT = (
    "You are a professional translator. "
    "Translate the following text from {source_lang} to {target_lang}. "
    "Output only the translation, no explanations."
)
_AUTO_DETECT_PROMPT = (
    "You are a professional translator. "
    "First detect the language of the input text, then translate it to {target_lang}. "
    "Output only the translation, no explanations."
)


class Provider(SoupProvider):
    name = "openai_compatible"
    prettyname = "OpenAI Compatible"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.INSTANCES | ProviderFeature.API_KEY | ProviderFeature.DETECTION
    settings_schema_id = f"{APP_ID}.openai-translator"

    defaults: ProviderDefaults = {
        "instance_url": "api.openai.com",
        "api_key": "",
        "src_langs": ["en", "zh-Hans", "ja", "fr", "es", "de"],
        "dest_langs": ["zh-Hans", "en", "ja", "fr", "es", "de"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.chars_limit = -1
        self._current_cancellable: Gio.Cancellable | None = None

    @property
    def completions_url(self) -> str:
        """OpenAI-compatible chat completions endpoint."""
        return self._build_versioned_url("/chat/completions")

    @property
    def models_url(self) -> str:
        """OpenAI-compatible models endpoint."""
        return self._build_versioned_url("/models")

    def _build_versioned_url(self, path: str, base_url: str | None = None) -> str:
        """Build a full API URL, auto-appending `/v1` only when no version segment exists."""
        url = (base_url or self.instance_url).rstrip("/")
        if "/v1" not in url and not re.search(r"/v\d+", url):
            url += "/v1"
        return self.format_url(url, path)

    async def init_trans(self) -> None:
        """Populate translation languages from Dialect's static CLDR language list."""
        for code in LANGUAGES:
            self.add_lang(code)

    async def validate_instance(self, url: str) -> bool:
        """Validate the instance URL by probing the OpenAI-compatible models endpoint."""
        test_url = self._build_versioned_url("/models", base_url=url)

        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        message = self.create_message("GET", test_url, headers=headers)
        raw_response = await self.send_and_read_and_process(
            message,
            check_common=False,
            return_json=False,
        )
        if message.get_status() in (401, 403):
            return True

        try:
            response = json.loads(raw_response) if raw_response else {}
        except json.JSONDecodeError:
            return False
        return isinstance(response, dict) and response.get("object") == "list" and "data" in response

    async def validate_api_key(self, key: str) -> bool:
        """Validate an API key against the configured models endpoint."""
        if not key.strip():
            return True

        headers = {"Authorization": f"Bearer {key}"}
        message = self.create_message("GET", self.models_url, headers=headers)
        raw_response = await self.send_and_read_and_process(
            message,
            check_common=False,
            return_json=False,
        )
        if message.get_status() in (401, 403):
            return False
        if message.get_status() < 200 or message.get_status() >= 300:
            return False

        try:
            response = json.loads(raw_response) if raw_response else {}
        except json.JSONDecodeError:
            return False
        return isinstance(response, dict)

    def _get_lang_display_name(self, code: str) -> str:
        """Return a human-readable language name, falling back to the language code."""
        return self.get_lang_name(code) or code

    def _append_missing_prompt_context(
        self,
        rendered_prompt: str,
        template: str,
        source_name: str,
        target_name: str,
    ) -> str:
        context: list[str] = []
        if "{source_lang}" not in template:
            context.append(f"Source language: {source_name}")
        if "{target_lang}" not in template:
            context.append(f"Target language: {target_name}")
        if not context:
            return rendered_prompt
        return f"{rendered_prompt}\n\n" + "\n".join(context)

    def _build_system_prompt(self, request: TranslationRequest) -> str:
        target_name = self._get_lang_display_name(request.dest)
        source_name = (
            "auto-detected language"
            if request.src == "auto"
            else self._get_lang_display_name(request.src)
        )
        custom_prompt = self.settings.system_prompt

        if custom_prompt:
            rendered_prompt = custom_prompt.replace("{source_lang}", source_name).replace(
                "{target_lang}",
                target_name,
            )
            return self._append_missing_prompt_context(rendered_prompt, custom_prompt, source_name, target_name)

        if request.src == "auto":
            return _AUTO_DETECT_PROMPT.format(target_lang=target_name)
        return _DEFAULT_PROMPT.format(source_lang=source_name, target_lang=target_name)

    def _build_messages(self, request: TranslationRequest) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._build_system_prompt(request)},
            {"role": "user", "content": request.text},
        ]

    def _cancel_ongoing(self) -> None:
        """Cancel any in-flight request and prepare a cancellable for the next one."""
        if self._current_cancellable and not self._current_cancellable.is_cancelled():
            self._current_cancellable.cancel()
        self._current_cancellable = Gio.Cancellable()

    async def translate(self, request: TranslationRequest) -> Translation:
        """Translate text through an OpenAI Chat Completions compatible endpoint."""
        self._cancel_ongoing()
        data: dict[str, Any] = {
            "model": self.settings.model_name,
            "messages": self._build_messages(request),
        }
        temperature = self.settings.temperature
        if temperature is not None:
            data["temperature"] = temperature

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = await self.post(
                self.completions_url,
                data=data,
                headers=headers,
                cancellable=self._current_cancellable,
            )
        except GLib.Error as exc:
            if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return Translation("", request)
            raise

        if not isinstance(response, dict):
            raise UnexpectedError(f"Unexpected response type: {type(response)}")

        choices = response.get("choices")
        if not choices or not isinstance(choices, list):
            raise UnexpectedError("No choices in response")

        choice = choices[0]
        if not isinstance(choice, dict):
            raise UnexpectedError("Unexpected choice object in response")

        message = choice.get("message")
        if not isinstance(message, dict):
            raise UnexpectedError("No message in response")

        content = message.get("content")
        if not isinstance(content, str):
            raise UnexpectedError("No content in response")

        return Translation(content.strip(), request)

    def check_known_errors(self, status: int, data: Any) -> None:
        """Raise Dialect provider errors for OpenAI-compatible error responses."""
        message = ""
        if isinstance(data, dict):
            error = data.get("error", {})
            if isinstance(error, dict):
                message = str(error.get("message", ""))
            elif error:
                message = str(error)

        match status:
            case 401:
                if not self.api_key:
                    raise APIKeyRequired(message)
                raise APIKeyInvalid(message)
            case 402 | 403:
                raise APIKeyInvalid(message)
            case 429:
                raise ServiceLimitReached(message)

        if status >= 500:
            raise RequestError(message or f"HTTP {status}")
        if status != 200:
            raise UnexpectedError(message or f"HTTP {status}")
