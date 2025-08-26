# Copyright 2025 Mufeed Ali
# Copyright 2025 Rafael Mardojai CM
# SPDX-License-Identifier: GPL-3.0-or-later

from dialect.providers.base import (
    ProviderCapability,
    ProviderFeature,
    ProviderLangComparison,
    Translation,
)
from dialect.providers.errors import (
    APIKeyRequired,
    UnexpectedError,
)
from dialect.providers.soup import SoupProvider


class Provider(SoupProvider):
    name = "kagi"
    prettyname = "Kagi Translate"

    capabilities = ProviderCapability.TRANSLATION
    features = ProviderFeature.DETECTION | ProviderFeature.API_KEY | ProviderFeature.API_KEY_REQUIRED
    lang_comp = ProviderLangComparison.DEEP

    defaults = {
        "instance_url": "",
        "api_key": "",
        "src_langs": ["en", "fr", "es", "de", "ja", "zh"],
        "dest_langs": ["fr", "es", "de", "en", "ja", "zh"],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.api_url = "translate.kagi.com/api"
        self.chars_limit = 20000  # Web UI limit

    @property
    def headers(self):
        return {"Content-Type": "application/json"}

    @property
    def lang_url(self):
        return self.format_url(self.api_url, "/list-languages", params={"token": self.api_key})

    @property
    def translate_url(self):
        return self.format_url(self.api_url, "/translate", params={"token": self.api_key})

    async def validate_api_key(self, key):
        """Validate the API key (session token)"""
        try:
            # Test session token by checking authentication status
            url = self.format_url(self.api_url, "/auth", params={"token": key})
            response = await self.get(url, self.headers)
            if response and isinstance(response, dict) and response["loggedIn"] is True:
                return True
        except (APIKeyRequired, UnexpectedError):
            return False
        return False

    async def init_trans(self):
        """Initialize translation capabilities by fetching supported languages"""
        languages = await self.get(self.lang_url, self.headers)

        if languages and isinstance(languages, list):
            for lang in languages:
                # Add language with lowercase code as per Kagi API convention
                self.add_lang(lang["language"].lower(), lang["name"])

    async def translate(self, request):
        """Translate text using Kagi API"""
        src, dest = self.denormalize_lang(request.src, request.dest)

        data = {
            "text": request.text,
            "source_lang": src if src != "auto" else "auto",
            "target_lang": dest,
            "skip_definition": True,  # Get translation only, no definitions
        }

        response = await self.post(self.translate_url, data, self.headers)

        if response and isinstance(response, dict):
            detected = None
            if "detected_language" in response and response["detected_language"]:
                detected = response["detected_language"].get("iso")

            translation = Translation(response["translation"], request, detected)
            return translation

        raise UnexpectedError("Failed reading the translation data")

    def check_known_errors(self, status, data):
        """Check for known error conditions in the response"""
        if not data:
            raise UnexpectedError("Response is empty")

        # Check for error field in response
        if isinstance(data, dict) and "error" in data:
            error = data["error"]

            if any(keyword in error.lower() for keyword in ["token", "unauthorized", "authentication"]):
                raise APIKeyRequired(f"Invalid session token: {error}")
            else:
                raise UnexpectedError(error)

        # Check HTTP status codes
        if status == 401:
            raise APIKeyRequired("Unauthorized - invalid session token")
        elif status == 403:
            raise APIKeyRequired("Forbidden - session token required")
        elif status != 200:
            raise UnexpectedError(f"HTTP {status} error")
